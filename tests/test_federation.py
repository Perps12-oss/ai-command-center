"""Tests for cross-workspace federation (P4).

Covers:
- WorkspaceRegistry CRUD
- FederatedWorldModel query merging and conflict detection
- FederationService EventBus integration
"""

from __future__ import annotations

import sqlite3

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    FEDERATION_CONFLICT_DETECTED,
    FEDERATION_QUERY_REQUEST,
    FEDERATION_QUERY_RESULT,
    FEDERATION_SYNC_COMPLETED,
    FEDERATION_WORKSPACE_REGISTERED,
    FEDERATION_WORKSPACE_UNREGISTERED,
)
from ai_command_center.core.world_model.federation.federated_world_model import FederatedWorldModel
from ai_command_center.core.world_model.federation.workspace_registry import WorkspaceRegistry
from ai_command_center.domain.federation import (
    FederatedNode,
    WorkspaceDescriptor,
    WorkspaceRole,
)
from ai_command_center.domain.world_model import Mutation, MutationType, Node
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.repositories.world_model_repository import IWorldModelRepository
from ai_command_center.services.federation_service import FederationService


# ── WorkspaceRegistry ──────────────────────────────────────────────────────


@pytest.fixture
def reg_conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


@pytest.fixture
def registry(reg_conn: sqlite3.Connection) -> WorkspaceRegistry:
    return WorkspaceRegistry(reg_conn)


def _descriptor(ws_id: str = "ws-1", name: str = "Test WS") -> WorkspaceDescriptor:
    return WorkspaceDescriptor(
        workspace_id=ws_id,
        name=name,
        role=WorkspaceRole.SECONDARY,
        db_path="/tmp/test.db",
        tags=("test",),
    )


def test_registry_register_and_get(registry: WorkspaceRegistry) -> None:
    d = _descriptor()
    registry.register(d)
    retrieved = registry.get("ws-1")
    assert retrieved is not None
    assert retrieved.workspace_id == "ws-1"
    assert retrieved.name == "Test WS"
    assert retrieved.role == WorkspaceRole.SECONDARY


def test_registry_get_nonexistent(registry: WorkspaceRegistry) -> None:
    assert registry.get("ghost") is None


def test_registry_upsert_on_re_register(registry: WorkspaceRegistry) -> None:
    registry.register(_descriptor(name="Old Name"))
    registry.register(_descriptor(name="New Name"))
    retrieved = registry.get("ws-1")
    assert retrieved is not None
    assert retrieved.name == "New Name"


def test_registry_unregister_returns_true(registry: WorkspaceRegistry) -> None:
    registry.register(_descriptor())
    assert registry.unregister("ws-1") is True
    assert registry.get("ws-1") is None


def test_registry_unregister_nonexistent_returns_false(registry: WorkspaceRegistry) -> None:
    assert registry.unregister("ghost") is False


def test_registry_list_all(registry: WorkspaceRegistry) -> None:
    registry.register(_descriptor("ws-1", "WS One"))
    registry.register(_descriptor("ws-2", "WS Two"))
    all_ws = registry.list_all()
    assert len(all_ws) == 2
    ids = {w.workspace_id for w in all_ws}
    assert ids == {"ws-1", "ws-2"}


def test_registry_list_by_role(registry: WorkspaceRegistry) -> None:
    registry.register(_descriptor("ws-primary", "Primary"))
    registry.register(WorkspaceDescriptor("ws-ro", "Read-Only", WorkspaceRole.READ_ONLY, "/db"))
    secondary = registry.list_by_role(WorkspaceRole.SECONDARY)
    assert len(secondary) == 1
    assert secondary[0].workspace_id == "ws-primary"


def test_registry_tags_survive_round_trip(registry: WorkspaceRegistry) -> None:
    d = WorkspaceDescriptor("ws-t", "Tagged", WorkspaceRole.SECONDARY, "/db", tags=("alpha", "beta"))
    registry.register(d)
    retrieved = registry.get("ws-t")
    assert retrieved is not None
    assert set(retrieved.tags) == {"alpha", "beta"}


def test_registry_schema_idempotent(reg_conn: sqlite3.Connection) -> None:
    r1 = WorkspaceRegistry(reg_conn)
    r1.register(_descriptor("ws-1"))
    r2 = WorkspaceRegistry(reg_conn)
    assert r2.get("ws-1") is not None


# ── Stub IWorldModelRepository ─────────────────────────────────────────────


class _StubRepo:
    """Minimal stub satisfying IWorldModelRepository for testing federation."""

    def __init__(self, nodes: list[Node] | None = None) -> None:
        self._nodes: dict[str, Node] = {n.id: n for n in (nodes or [])}
        self._mutations: list[Mutation] = []

    def apply_mutation(self, mutation: Mutation) -> None:
        self._mutations.append(mutation)

    def save_node(self, node: Node, correlation: CorrelationContext) -> None:
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def delete_node(self, node_id: str, correlation: CorrelationContext) -> None:
        self._nodes.pop(node_id, None)

    def save_edge(self, edge, correlation: CorrelationContext) -> None:
        pass

    def get_edges(self, node_id: str, direction: str = "both") -> list:
        return []

    def delete_edge(self, edge_id: str, correlation: CorrelationContext) -> None:
        pass

    def append_mutation(self, mutation: Mutation) -> None:
        self._mutations.append(mutation)

    def list_mutations(self, limit: int = 100, after_id: str = "") -> list[Mutation]:
        return self._mutations[-limit:]

    def replay_mutations(self, limit: int = 5) -> list[Mutation]:
        return self._mutations[-limit:]


def _node(node_id: str, node_type: str = "resource") -> Node:
    return Node(id=node_id, type=node_type, attributes={"name": f"Node-{node_id}"})


def _mutation_for(node: Node) -> Mutation:
    return Mutation(
        id=f"m-{node.id}",
        correlation=CorrelationContext.new(),
        type=MutationType.CREATE_NODE,
        payload={"node": node.to_payload()},
    )


# ── FederatedWorldModel ────────────────────────────────────────────────────


def test_federated_query_returns_primary_nodes() -> None:
    n1 = _node("n-1", "workspace")
    stub_primary = _StubRepo([n1])
    stub_primary.append_mutation(_mutation_for(n1))

    federation = FederatedWorldModel(primary_repo=stub_primary)
    result = federation.query_nodes()
    assert len(result.nodes) == 1
    assert result.nodes[0].node_id == "n-1"
    assert result.nodes[0].workspace_id == "primary"


def test_federated_query_merges_secondary() -> None:
    n1 = _node("n-1", "workspace")
    n2 = _node("n-2", "goal")
    primary = _StubRepo([n1])
    primary.append_mutation(_mutation_for(n1))
    secondary = _StubRepo([n2])
    secondary.append_mutation(_mutation_for(n2))

    federation = FederatedWorldModel(primary_repo=primary)
    d = _descriptor("ws-sec", "Secondary")
    federation.add_workspace(d, secondary)

    result = federation.query_nodes()
    assert len(result.nodes) == 2
    ws_ids = {n.workspace_id for n in result.nodes}
    assert ws_ids == {"primary", "ws-sec"}


def test_federated_query_workspace_count() -> None:
    primary = _StubRepo()
    secondary1 = _StubRepo()
    secondary2 = _StubRepo()
    federation = FederatedWorldModel(primary_repo=primary)
    federation.add_workspace(_descriptor("ws-1"), secondary1)
    federation.add_workspace(_descriptor("ws-2", "WS2"), secondary2)
    result = federation.query_nodes()
    assert result.workspace_count == 3


def test_federated_remove_workspace() -> None:
    n1, n2 = _node("n-1"), _node("n-2")
    primary = _StubRepo([n1])
    primary.append_mutation(_mutation_for(n1))
    secondary = _StubRepo([n2])
    secondary.append_mutation(_mutation_for(n2))

    federation = FederatedWorldModel(primary_repo=primary)
    federation.add_workspace(_descriptor("ws-sec"), secondary)
    assert federation.remove_workspace("ws-sec") is True
    result = federation.query_nodes()
    assert all(n.workspace_id == "primary" for n in result.nodes)


def test_federated_remove_nonexistent_returns_false() -> None:
    federation = FederatedWorldModel(primary_repo=_StubRepo())
    assert federation.remove_workspace("ghost") is False


def test_federated_conflict_detection() -> None:
    n1_primary = _node("shared-id", "workspace")
    n1_secondary = _node("shared-id", "goal")

    primary = _StubRepo([n1_primary])
    primary.append_mutation(_mutation_for(n1_primary))
    secondary = _StubRepo([n1_secondary])
    secondary.append_mutation(_mutation_for(n1_secondary))

    federation = FederatedWorldModel(primary_repo=primary)
    federation.add_workspace(_descriptor("ws-sec"), secondary)

    conflicts = federation.detect_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0]["node_id"] == "shared-id"
    assert conflicts[0]["conflict_type"] == "type_mismatch"


def test_federated_no_conflicts_when_types_match() -> None:
    n1 = _node("shared-id", "workspace")
    n2 = _node("shared-id", "workspace")

    primary = _StubRepo([n1])
    primary.append_mutation(_mutation_for(n1))
    secondary = _StubRepo([n2])
    secondary.append_mutation(_mutation_for(n2))

    federation = FederatedWorldModel(primary_repo=primary)
    federation.add_workspace(_descriptor("ws-sec"), secondary)

    conflicts = federation.detect_conflicts()
    assert conflicts == []


def test_federated_sync_status_tracks_state() -> None:
    n1 = _node("n-1")
    secondary = _StubRepo([n1])
    secondary.append_mutation(_mutation_for(n1))

    federation = FederatedWorldModel(primary_repo=_StubRepo())
    federation.add_workspace(_descriptor("ws-sec"), secondary)
    federation.query_nodes()

    status = federation.get_sync_status()
    assert len(status) == 1
    assert status[0].workspace_id == "ws-sec"


# ── FederationService (EventBus integration) ───────────────────────────────


def _make_federation_stack() -> tuple[EventBus, FederationService, FederatedWorldModel]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    registry = WorkspaceRegistry(conn)
    primary = _StubRepo()
    federated = FederatedWorldModel(primary_repo=primary)
    bus = EventBus()
    service = FederationService(bus, registry, federated)
    service.start()
    return bus, service, federated


def test_federation_service_query_request_publishes_result() -> None:
    bus, service, _ = _make_federation_stack()
    results: list[dict] = []
    bus.subscribe(FEDERATION_QUERY_RESULT, lambda e: results.append(dict(e.payload)))

    bus.publish(FEDERATION_QUERY_REQUEST, {"request_id": "req-1", "query": ""}, source="test")
    service.stop()

    assert len(results) == 1
    assert results[0]["request_id"] == "req-1"
    assert results[0]["error"] is None


def test_federation_service_sync_completed_on_register() -> None:
    bus, service, _ = _make_federation_stack()
    synced: list[dict] = []
    bus.subscribe(FEDERATION_SYNC_COMPLETED, lambda e: synced.append(dict(e.payload)))

    bus.publish(FEDERATION_WORKSPACE_REGISTERED, {
        "workspace_id": "ws-new",
        "name": "New WS",
        "role": "read_only",
        "db_path": ":memory:",
    }, source="test")
    service.stop()

    assert len(synced) >= 1
    assert synced[0]["workspace_id"] == "ws-new"


def test_federation_service_unregister_removes_workspace() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    registry = WorkspaceRegistry(conn)
    d = _descriptor("ws-1")
    registry.register(d)

    primary = _StubRepo()
    federated = FederatedWorldModel(primary_repo=primary)
    bus = EventBus()
    service = FederationService(bus, registry, federated)
    service.start()

    bus.publish(FEDERATION_WORKSPACE_UNREGISTERED, {"workspace_id": "ws-1"}, source="test")
    service.stop()

    assert registry.get("ws-1") is None


def test_federation_service_invalid_descriptor_does_not_crash() -> None:
    bus, service, _ = _make_federation_stack()
    bus.publish(FEDERATION_WORKSPACE_REGISTERED, {"bad_key": "no_workspace_id"}, source="test")
    service.stop()
