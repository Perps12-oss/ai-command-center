"""Stage 2 Slice 1 — State Authority query contract surface."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import STATE_CONTEXT_BUILT
from ai_command_center.core.world_model.world_model import WorldModel, mutation_for_node
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.state_authority import (
    MutationReceipt,
    ProjectionScope,
    StateDelta,
    StateQuery,
)
from ai_command_center.domain.state_context import StateContext
from ai_command_center.domain.world_model import MutationType, Node
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.state_authority_service import StateAuthorityService


def _world() -> WorldModel:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    repo = SQLiteWorldModelRepository(conn)
    wm = WorldModel(repo)
    corr = CorrelationContext.new(goal_id="seed")
    wm.apply(
        mutation_for_node(
            mutation_id="mut-note-1",
            node=Node("n-note-1", "note", {"title": "Ship Stage 2"}),
            correlation=corr,
            mutation_type=MutationType.CREATE_NODE,
        )
    )
    wm.apply(
        mutation_for_node(
            mutation_id="mut-app-1",
            node=Node("n-app-1", "application", {"name": "ACC"}),
            correlation=corr,
            mutation_type=MutationType.CREATE_NODE,
        )
    )
    return wm


def test_query_returns_state_projection_and_publishes_built() -> None:
    bus = EventBus()
    seen: list[dict] = []
    bus.subscribe(STATE_CONTEXT_BUILT, lambda e: seen.append(dict(e.payload or {})))
    sa = StateAuthorityService(bus, _world())
    sa.start()

    projection = sa.query(StateQuery(text="Ship Stage", workspace_id="ws-1"))
    assert isinstance(projection, StateContext)
    assert projection.workspace_id == "ws-1"
    assert projection.query_text == "Ship Stage"
    assert any(e.get("id") == "n-note-1" for e in projection.entities)
    assert seen and seen[0].get("workspace_id") == "ws-1"
    sa.stop()


def test_query_entity_type_filter() -> None:
    bus = EventBus()
    sa = StateAuthorityService(bus, _world())
    sa.start()
    projection = sa.query(
        StateQuery(entity_types=("application",), include_memories=False, include_goals=False)
    )
    types = {e.get("type") for e in projection.entities}
    assert types == {"application"}
    sa.stop()


def test_project_delegates_to_query() -> None:
    bus = EventBus()
    sa = StateAuthorityService(bus, _world())
    sa.start()
    via_kwargs = sa.project(text="ACC", workspace_id="ws-2")
    via_scope = sa.project(scope=ProjectionScope(text="ACC", workspace_id="ws-2"))
    assert via_kwargs.workspace_id == "ws-2"
    assert via_scope.workspace_id == "ws-2"
    assert any(e.get("id") == "n-app-1" for e in via_kwargs.entities)
    sa.stop()


def test_mutate_returns_deferred_receipt() -> None:
    bus = EventBus()
    sa = StateAuthorityService(bus, _world())
    sa.start()
    receipt = sa.mutate(
        StateDelta(workspace_id="ws-1", correlation_id="c1", operations=({"op": "noop"},))
    )
    assert isinstance(receipt, MutationReceipt)
    assert receipt.ok is False
    assert "not unified" in receipt.message.lower() or "BrainRuntime" in receipt.message
    assert receipt.correlation_id == "c1"
    sa.stop()
