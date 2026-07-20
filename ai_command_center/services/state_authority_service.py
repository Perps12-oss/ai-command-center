"""State Authority — World Model / workspace reality projection before decisions.

Builds StateContext from WorldModelQueryService (+ Intent + ContextProjection)
so ExecutionAuthority and Planner can decide from known state, not text alone.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    STATE_CONTEXT_BUILT,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.domain.state_context import StateContext
from ai_command_center.services.base import BaseService
from ai_command_center.core.state_intelligence.context_projection_service import ContextProjectionService
from ai_command_center.core.state_intelligence.world_model_query_service import WorldModelQueryService

_logger = logging.getLogger(__name__)


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
        query_service: WorldModelQueryService | None = None,
        projection_service: ContextProjectionService | None = None,
    ) -> None:
        super().__init__(bus)
        self._world_model = world_model
        self._memory_lookup = memory_lookup
        self._goal_lookup = goal_lookup
        self._query_service = query_service
        self._projection_service = projection_service
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

    def project(
        self,
        *,
        text: str = "",
        workspace_id: str = "",
    ) -> StateContext:
        """Query World Model (+ Intent) and return budgeted decision context."""
        ws = (workspace_id or self._active_workspace_id).strip()

        if self._query_service is not None:
            raw = self._query_service.project_state(text=text, workspace_id=ws)
            if self._projection_service is not None:
                context = self._projection_service.project(
                    text=text,
                    workspace_id=ws,
                    state_context=raw,
                )
            else:
                context = raw
        else:
            context = self._legacy_project(text=text, workspace_id=ws)

        self._bus.publish(
            STATE_CONTEXT_BUILT,
            context.to_dict(),
            source=self.name,
        )
        _logger.info(
            "state_authority.project workspace=%s entities=%d memories=%d goals=%d",
            ws,
            len(context.entities),
            len(context.memories),
            len(context.goals),
        )
        return context

    def _legacy_project(self, *, text: str, workspace_id: str) -> StateContext:
        """Fallback when query service is not wired (tests)."""
        import re

        token_re = re.compile(r"[a-z0-9_]{3,}", re.IGNORECASE)
        tokens = set(token_re.findall(text.lower()))
        entities: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        cached = self._world_model.iter_cached_nodes()
        if not cached:
            self._world_model.recover(replay_limit=500)
            cached = self._world_model.iter_cached_nodes()

        for node in cached:
            label = str(
                node.attributes.get("name")
                or node.attributes.get("title")
                or node.attributes.get("label")
                or node.id
            )
            blob = f"{node.type} {label} {node.attributes}".lower()
            if tokens and not any(tok in blob for tok in tokens):
                if node.type not in {
                    "note",
                    "memory",
                    "goal",
                    "application",
                    "task",
                    "workspace",
                    "execution_run",
                }:
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
        if self._memory_lookup is not None and text.strip():
            try:
                memories = list(
                    self._memory_lookup(text.strip(), workspace_id=workspace_id) or []
                )
            except Exception as exc:  # noqa: BLE001
                _logger.warning("state_authority.memory_lookup_failed: %s", exc)

        goals: list[dict[str, Any]] = []
        if self._goal_lookup is not None:
            try:
                goals = list(self._goal_lookup(workspace_id=workspace_id) or [])
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
        if workspace_id:
            summary_parts.append(f"active_workspace={workspace_id}")

        return StateContext(
            workspace_id=workspace_id,
            entities=tuple(entities[:40]),
            relationships=tuple(relationships[:80]),
            memories=tuple(memories[:10]),
            goals=tuple(goals[:10]),
            summary="; ".join(summary_parts),
            query_text=text.strip(),
        )
