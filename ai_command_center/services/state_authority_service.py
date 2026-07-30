"""State Authority — World Model / workspace reality projection before decisions.

Implements the Stage 2 contract surface:

* ``query(StateQuery) -> StateProjection`` — structured read (no side effects
  beyond publishing ``STATE_CONTEXT_BUILT`` for observability)
* ``project(...)`` — convenience wrapper used by ExecutionAuthority today
* ``mutate(StateDelta)`` — World Model node + edge ops with ``MutationReceipt``

See ``docs/architecture/STATE_AUTHORITY_CONTRACT.md``.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable
from typing import Any, Protocol

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    STATE_CONTEXT_BUILT,
    WORLD_MODEL_MUTATION_APPLIED,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.core.world_model.world_model import (
    WorldModel,
    mutation_for_edge,
    mutation_for_node,
)
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.state_authority import (
    MutationReceipt,
    ProjectionScope,
    StateDelta,
    StateProjection,
    StateQuery,
)
from ai_command_center.domain.state_context import StateContext
from ai_command_center.domain.world_model import Edge, Mutation, MutationType, Node
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9_]{3,}", re.IGNORECASE)

_ALWAYS_KEEP_TYPES = frozenset(
    {
        "note",
        "memory",
        "goal",
        "application",
        "task",
        "workspace",
        "execution_run",
    }
)

_NODE_WRITE_OPS = frozenset({"create_node", "update_node", "upsert_node"})
_NODE_DELETE_OPS = frozenset({"delete_node"})
_EDGE_WRITE_OPS = frozenset({"create_edge"})
_EDGE_DELETE_OPS = frozenset({"delete_edge"})
_SUPPORTED_OPS = _NODE_WRITE_OPS | _NODE_DELETE_OPS | _EDGE_WRITE_OPS | _EDGE_DELETE_OPS


def _correlation_for_delta(delta: StateDelta) -> CorrelationContext:
    if delta.correlation_id.strip():
        return CorrelationContext(
            correlation_id=delta.correlation_id.strip(),
            goal_id="",
            action_id="state_authority.mutate",
        )
    return CorrelationContext.new(action_id="state_authority.mutate")


def _node_from_op(raw: dict[str, Any], *, workspace_id: str) -> Node | None:
    node_raw = raw.get("node") if isinstance(raw.get("node"), dict) else raw
    if not isinstance(node_raw, dict):
        return None
    node_id = str(node_raw.get("id") or "").strip()
    if not node_id:
        return None
    attrs = dict(node_raw.get("attributes") or {})
    if workspace_id and "workspace_id" not in attrs:
        attrs["workspace_id"] = workspace_id
    return Node(
        id=node_id,
        type=str(node_raw.get("type") or "resource"),
        attributes=attrs,
    )


def _edge_from_op(raw: dict[str, Any]) -> Edge | None:
    edge_raw = raw.get("edge") if isinstance(raw.get("edge"), dict) else raw
    if not isinstance(edge_raw, dict):
        return None
    edge_id = str(edge_raw.get("id") or "").strip()
    from_id = str(edge_raw.get("from_node_id") or "").strip()
    to_id = str(edge_raw.get("to_node_id") or "").strip()
    if not edge_id or not from_id or not to_id:
        return None
    return Edge(
        id=edge_id,
        from_node_id=from_id,
        to_node_id=to_id,
        type=str(edge_raw.get("type") or "related"),
        attributes=dict(edge_raw.get("attributes") or {}),
    )


class StateAuthority(Protocol):
    """Behavioral contract — sole approved query / mutate / project path."""

    def query(self, query: StateQuery) -> StateProjection:
        """Read authoritative workspace reality for a scope. No store writes."""

    def mutate(self, delta: StateDelta) -> MutationReceipt:
        """Apply an authoritative state change. Returns a correlatable receipt."""

    def project(
        self,
        *,
        text: str = "",
        workspace_id: str = "",
    ) -> StateContext:
        """Build decision-facing projection (ExecutionAuthority convenience)."""


class StateAuthorityService(BaseService):
    """Sole owner of pre-decision state projection from World Model."""

    name = "state_authority"

    def __init__(
        self,
        bus,
        world_model: WorldModel,
        *,
        memory_lookup: Callable[..., list[dict[str, Any]]] | None = None,
        goal_lookup: Callable[..., list[dict[str, Any]]] | None = None,
    ) -> None:
        super().__init__(bus)
        self._world_model = world_model
        self._memory_lookup = memory_lookup
        self._goal_lookup = goal_lookup
        self._unsubscribers: list[Callable[[], None]] = []
        self._active_workspace_id: str = ""

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_ACTIVE, self._on_workspace_active)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_DEACTIVATED, self._on_workspace_deactivated)
        )
        # Warm cache from journal so queries have content after restart.
        self._world_model.recover(replay_limit=500)

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_workspace_active(self, event: Event) -> None:
        self._active_workspace_id = str(event.payload.get("workspace_id", "")).strip()

    def _on_workspace_deactivated(self, event: Event) -> None:
        cleared = str(event.payload.get("workspace_id", "")).strip()
        if not cleared or cleared == self._active_workspace_id:
            self._active_workspace_id = ""

    def query(self, query: StateQuery) -> StateProjection:
        """Structured read of World Model (+ optional memory/goal signals)."""
        ws = (query.workspace_id or self._active_workspace_id).strip()
        text = query.text.strip()
        tokens = set(_TOKEN_RE.findall(text.lower()))
        type_filter = {t.lower() for t in query.entity_types if t}
        entities: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        # Prefer live cache; recover lightly if empty (restart path).
        cached = self._world_model.iter_cached_nodes()
        if not cached:
            self._world_model.recover(replay_limit=500)
            cached = self._world_model.iter_cached_nodes()

        for node in cached:
            if type_filter and str(node.type).lower() not in type_filter:
                continue
            label = str(
                node.attributes.get("name")
                or node.attributes.get("title")
                or node.attributes.get("label")
                or node.id
            )
            blob = f"{node.type} {label} {node.attributes}".lower()
            if tokens and not any(tok in blob for tok in tokens):
                # Keep domain-typed nodes always so reconstruction stays available.
                if node.type not in _ALWAYS_KEEP_TYPES:
                    continue
            entities.append(
                {
                    "id": node.id,
                    "type": node.type,
                    "label": label,
                    "attributes": dict(node.attributes),
                }
            )
            for edge in self._world_model.get_edges(node.id, "out"):
                relationships.append(
                    {
                        "id": edge.id,
                        "from_node_id": edge.from_node_id,
                        "to_node_id": edge.to_node_id,
                        "type": edge.type,
                    }
                )

        memories: list[dict[str, Any]] = []
        if query.include_memories and self._memory_lookup is not None and text:
            try:
                memories = list(self._memory_lookup(text, workspace_id=ws) or [])
            except Exception as exc:  # noqa: BLE001 — projection must not fail intake
                _logger.warning("state_authority.memory_lookup_failed: %s", exc)

        goals: list[dict[str, Any]] = []
        if query.include_goals and self._goal_lookup is not None:
            try:
                goals = list(self._goal_lookup(workspace_id=ws) or [])
            except Exception as exc:  # noqa: BLE001
                _logger.warning("state_authority.goal_lookup_failed: %s", exc)

        summary_parts: list[str] = []
        if entities:
            summary_parts.append(
                f"{len(entities)} known entities: "
                + ", ".join(f"{e['type']}:{e['label']}" for e in entities[:6])
            )
        if memories:
            summary_parts.append(f"{len(memories)} related memories")
        if goals:
            summary_parts.append(
                f"{len(goals)} goals: "
                + ", ".join(str(g.get("title", "")) for g in goals[:4])
            )
        if ws:
            summary_parts.append(f"active_workspace={ws}")

        context = StateContext(
            workspace_id=ws,
            entities=tuple(entities[:40]),
            relationships=tuple(relationships[:80]),
            memories=tuple(memories[:10]),
            goals=tuple(goals[:10]),
            summary="; ".join(summary_parts),
            query_text=text,
        )
        self._bus.publish(
            STATE_CONTEXT_BUILT,
            context.to_dict(),
            source=self.name,
        )
        _logger.info(
            "state_authority.query workspace=%s entities=%d memories=%d goals=%d",
            ws,
            len(context.entities),
            len(context.memories),
            len(context.goals),
        )
        return context

    def project(
        self,
        *,
        text: str = "",
        workspace_id: str = "",
        scope: ProjectionScope | None = None,
    ) -> StateContext:
        """Decision-facing projection — delegates to :meth:`query`."""
        if scope is not None:
            text = scope.text or text
            workspace_id = scope.workspace_id or workspace_id
        return self.query(
            StateQuery(workspace_id=workspace_id, text=text),
        )

    def mutate(self, delta: StateDelta) -> MutationReceipt:
        """Apply authoritative World Model node/edge mutations (Stage 2 Slice 4).

        Supported ``StateDelta.operations``:

        * ``{"op": "create_node"|"update_node"|"upsert_node", "node": {...}}``
        * ``{"op": "delete_node", "node_id": "..."}``
        * ``{"op": "create_edge", "edge": {...}}``
        * ``{"op": "delete_edge", "edge_id": "..."}``

        Goals / workflows / memory remain outside this surface (shadow SoT).
        Orchestration may still use ``RUNTIME_ACTION_REQUEST`` → BrainRuntime;
        callers that go through State Authority must not invent a parallel store.
        """
        if not delta.operations:
            return MutationReceipt(
                workspace_id=delta.workspace_id,
                ok=False,
                message="StateDelta.operations is empty",
                correlation_id=delta.correlation_id,
            )

        correlation = _correlation_for_delta(delta)
        applied: list[dict[str, Any]] = []
        errors: list[str] = []

        for index, raw in enumerate(delta.operations):
            if not isinstance(raw, dict):
                errors.append(f"op[{index}]: expected dict")
                continue
            op = str(raw.get("op") or "").strip().lower()
            if op not in _SUPPORTED_OPS:
                errors.append(
                    f"op[{index}]: unsupported op {op!r} "
                    f"(supported: {sorted(_SUPPORTED_OPS)})"
                )
                continue

            mutation_id = str(raw.get("mutation_id") or f"sa-{uuid.uuid4().hex[:12]}")
            try:
                if op in _NODE_WRITE_OPS:
                    node = _node_from_op(raw, workspace_id=delta.workspace_id)
                    if node is None or not node.id:
                        errors.append(f"op[{index}]: node.id required")
                        continue
                    if op == "create_node":
                        mtype = MutationType.CREATE_NODE
                    elif op == "update_node":
                        mtype = MutationType.UPDATE_NODE
                    else:
                        # upsert_node — prefer UPDATE when present, else CREATE
                        existing = self._world_model.get_node(node.id)
                        mtype = (
                            MutationType.UPDATE_NODE
                            if existing is not None
                            else MutationType.CREATE_NODE
                        )
                    mutation = mutation_for_node(
                        mutation_id=mutation_id,
                        node=node,
                        correlation=correlation,
                        mutation_type=mtype,
                    )
                    self._world_model.apply(mutation)
                    self._bus.publish(
                        WORLD_MODEL_MUTATION_APPLIED,
                        {"mutation": mutation.to_payload()},
                        source=self.name,
                    )
                    applied.append(
                        {
                            "op": op,
                            "mutation_id": mutation.id,
                            "mutation_type": mutation.type.value,
                            "node_id": node.id,
                        }
                    )
                elif op in _NODE_DELETE_OPS:
                    node_id = str(raw.get("node_id") or "").strip()
                    if not node_id and isinstance(raw.get("node"), dict):
                        node_id = str(raw["node"].get("id") or "").strip()
                    if not node_id:
                        errors.append(f"op[{index}]: node_id required")
                        continue
                    mutation = Mutation(
                        id=mutation_id,
                        correlation=correlation,
                        type=MutationType.DELETE_NODE,
                        payload={"node_id": node_id},
                    )
                    self._world_model.apply(mutation)
                    self._bus.publish(
                        WORLD_MODEL_MUTATION_APPLIED,
                        {"mutation": mutation.to_payload()},
                        source=self.name,
                    )
                    applied.append(
                        {
                            "op": op,
                            "mutation_id": mutation.id,
                            "mutation_type": mutation.type.value,
                            "node_id": node_id,
                        }
                    )
                elif op in _EDGE_WRITE_OPS:
                    edge = _edge_from_op(raw)
                    if edge is None:
                        errors.append(
                            f"op[{index}]: edge.id, from_node_id, to_node_id required"
                        )
                        continue
                    mutation = mutation_for_edge(
                        mutation_id=mutation_id,
                        edge=edge,
                        correlation=correlation,
                        mutation_type=MutationType.CREATE_EDGE,
                    )
                    self._world_model.apply(mutation)
                    self._bus.publish(
                        WORLD_MODEL_MUTATION_APPLIED,
                        {"mutation": mutation.to_payload()},
                        source=self.name,
                    )
                    applied.append(
                        {
                            "op": op,
                            "mutation_id": mutation.id,
                            "mutation_type": mutation.type.value,
                            "edge_id": edge.id,
                            "from_node_id": edge.from_node_id,
                            "to_node_id": edge.to_node_id,
                        }
                    )
                else:  # delete_edge
                    edge_id = str(raw.get("edge_id") or "").strip()
                    if not edge_id and isinstance(raw.get("edge"), dict):
                        edge_id = str(raw["edge"].get("id") or "").strip()
                    if not edge_id:
                        errors.append(f"op[{index}]: edge_id required")
                        continue
                    mutation = Mutation(
                        id=mutation_id,
                        correlation=correlation,
                        type=MutationType.DELETE_EDGE,
                        payload={"edge_id": edge_id},
                    )
                    self._world_model.apply(mutation)
                    self._bus.publish(
                        WORLD_MODEL_MUTATION_APPLIED,
                        {"mutation": mutation.to_payload()},
                        source=self.name,
                    )
                    applied.append(
                        {
                            "op": op,
                            "mutation_id": mutation.id,
                            "mutation_type": mutation.type.value,
                            "edge_id": edge_id,
                        }
                    )
            except Exception as exc:  # noqa: BLE001 — receipt must report failure
                _logger.warning("state_authority.mutate_failed op=%s: %s", op, exc)
                errors.append(f"op[{index}]: {exc}")

        ok = bool(applied) and not errors
        if applied and errors:
            message = (
                f"partial apply: {len(applied)} ok, {len(errors)} failed — "
                + "; ".join(errors)
            )
            ok = False
        elif errors:
            message = "; ".join(errors)
        else:
            message = f"applied {len(applied)} world-model mutation(s)"

        _logger.info(
            "state_authority.mutate workspace=%s applied=%d ok=%s",
            delta.workspace_id,
            len(applied),
            ok,
        )
        return MutationReceipt(
            workspace_id=delta.workspace_id,
            ok=ok,
            message=message,
            correlation_id=correlation.correlation_id,
            applied=tuple(applied),
        )
