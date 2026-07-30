"""State Authority — World Model / workspace reality projection before decisions.

Implements the Stage 2 contract surface:

* ``query(StateQuery) -> StateProjection`` — structured read (no side effects
  beyond publishing ``STATE_CONTEXT_BUILT`` for observability)
* ``project(...)`` — convenience wrapper used by ExecutionAuthority today
* ``mutate(StateDelta)`` — surface reserved; World Model mutations remain on
  the BrainRuntime / ``RUNTIME_ACTION_REQUEST`` path until unified

See ``docs/architecture/STATE_AUTHORITY_CONTRACT.md``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any, Protocol

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    STATE_CONTEXT_BUILT,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.domain.state_authority import (
    MutationReceipt,
    ProjectionScope,
    StateDelta,
    StateProjection,
    StateQuery,
)
from ai_command_center.domain.state_context import StateContext
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
        """Authoritative mutate surface — not unified in Stage 2 Slice 1.

        Interim path: World Model mutations continue via BrainRuntime on
        ``RUNTIME_ACTION_REQUEST``. Callers must not invent a parallel SoT.
        """
        return MutationReceipt(
            workspace_id=delta.workspace_id,
            ok=False,
            message=(
                "StateAuthority.mutate is not unified yet; "
                "use RUNTIME_ACTION_REQUEST → BrainRuntime → WorldModel "
                "(see STATE_AUTHORITY_CONTRACT.md Stage 2+)."
            ),
            correlation_id=delta.correlation_id,
        )
