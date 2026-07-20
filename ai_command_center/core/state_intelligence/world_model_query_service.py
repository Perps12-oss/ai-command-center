"""WorldModelQueryService — Reality + Intent lookups for planners."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.domain.state_context import StateContext
from ai_command_center.services.base import BaseService
from ai_command_center.core.state_intelligence.execution_intent_registry import ExecutionIntentRegistry

_TOKEN_RE = re.compile(r"[a-z0-9_]{3,}", re.IGNORECASE)
_KEEP_TYPES = frozenset(
    {"note", "memory", "goal", "application", "task", "workspace", "execution_run"}
)


class WorldModelQueryService(BaseService):
    """Entity / relationship / timeline / workspace / goal / memory / app lookup."""

    name = "world_model_query"

    def __init__(
        self,
        bus,
        world_model: WorldModel,
        *,
        intent_registry: ExecutionIntentRegistry | None = None,
        memory_lookup: Callable[..., list[dict[str, Any]]] | None = None,
        goal_lookup: Callable[..., list[dict[str, Any]]] | None = None,
    ) -> None:
        super().__init__(bus)
        self._world_model = world_model
        self._intent_registry = intent_registry
        self._memory_lookup = memory_lookup
        self._goal_lookup = goal_lookup

    def _on_load(self) -> None:
        return

    def _on_unload(self) -> None:
        return

    def query_entities(
        self,
        *,
        text: str = "",
        workspace_id: str = "",
        node_types: frozenset[str] | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        tokens = set(_TOKEN_RE.findall(text.lower()))
        keep = node_types or _KEEP_TYPES
        cached = self._world_model.iter_cached_nodes()
        if not cached:
            self._world_model.recover(replay_limit=500)
            cached = self._world_model.iter_cached_nodes()

        entities: list[dict[str, Any]] = []
        for node in cached:
            label = str(
                node.attributes.get("name")
                or node.attributes.get("title")
                or node.attributes.get("label")
                or node.id
            )
            blob = f"{node.type} {label} {node.attributes}".lower()
            if tokens and not any(tok in blob for tok in tokens):
                if node.type not in keep:
                    continue
            if workspace_id:
                node_ws = str(node.attributes.get("workspace_id") or "")
                if node_ws and node_ws != workspace_id and node.type != "workspace":
                    continue
            entities.append(
                {
                    "id": node.id,
                    "type": node.type,
                    "label": label,
                    "attributes": dict(node.attributes),
                }
            )
            if len(entities) >= limit:
                break
        return entities

    def query_relationships(
        self,
        node_ids: list[str],
        *,
        depth: int = 1,
        limit: int = 80,
    ) -> list[dict[str, Any]]:
        relationships: list[dict[str, Any]] = []
        seen: set[str] = set()
        frontier = list(node_ids)
        for _ in range(max(1, depth)):
            next_frontier: list[str] = []
            for node_id in frontier:
                for edge in self._world_model.get_edges(node_id, "both"):
                    if edge.id in seen:
                        continue
                    seen.add(edge.id)
                    relationships.append(
                        {
                            "id": edge.id,
                            "from_node_id": edge.from_node_id,
                            "to_node_id": edge.to_node_id,
                            "type": edge.type,
                            "attributes": dict(edge.attributes),
                            "status": edge.attributes.get("status", ""),
                            "confidence": edge.attributes.get("confidence"),
                            "verified_at": edge.attributes.get("verified_at", ""),
                            "source": edge.attributes.get("source", ""),
                        }
                    )
                    other = (
                        edge.to_node_id
                        if edge.from_node_id == node_id
                        else edge.from_node_id
                    )
                    next_frontier.append(other)
                    if len(relationships) >= limit:
                        return relationships
            frontier = next_frontier
        return relationships

    def query_intents(self, *, workspace_id: str = "") -> list[dict[str, Any]]:
        if self._intent_registry is None:
            return []
        return self._intent_registry.to_projection_dicts(workspace_id=workspace_id)

    def query_memories(self, text: str, *, workspace_id: str = "") -> list[dict[str, Any]]:
        if self._memory_lookup is None or not text.strip():
            return []
        try:
            return list(self._memory_lookup(text.strip(), workspace_id=workspace_id) or [])
        except Exception:  # noqa: BLE001
            return []

    def query_goals(self, *, workspace_id: str = "") -> list[dict[str, Any]]:
        if self._goal_lookup is None:
            return []
        try:
            return list(self._goal_lookup(workspace_id=workspace_id) or [])
        except Exception:  # noqa: BLE001
            return []

    def project_state(
        self,
        *,
        text: str = "",
        workspace_id: str = "",
    ) -> StateContext:
        """Build StateContext from World Model + in-flight Intent."""
        entities = self.query_entities(text=text, workspace_id=workspace_id)
        relationships = self.query_relationships(
            [e["id"] for e in entities[:20]],
            depth=2,
        )
        memories = self.query_memories(text, workspace_id=workspace_id)
        goals = self.query_goals(workspace_id=workspace_id)
        intents = self.query_intents(workspace_id=workspace_id)

        # Surface in-flight intents as synthetic entities so planners see them.
        for intent in intents:
            entities.append(
                {
                    "id": f"intent:{intent['intent_id']}",
                    "type": "execution_intent",
                    "label": intent.get("text") or intent["intent_id"],
                    "attributes": {
                        "kind": intent.get("kind"),
                        "status": intent.get("status"),
                        "capability": intent.get("capability"),
                        "in_flight": True,
                    },
                }
            )

        summary_parts: list[str] = []
        if entities:
            summary_parts.append(
                f"{len(entities)} known entities: "
                + ", ".join(f"{e['type']}:{e['label']}" for e in entities[:6])
            )
        if intents:
            summary_parts.append(f"{len(intents)} in-flight intents")
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
