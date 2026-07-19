"""State context projection — World Model as decision input."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class StateContext:
    """Snapshot of workspace reality used before planning/execution."""

    workspace_id: str = ""
    entities: tuple[dict[str, Any], ...] = ()
    relationships: tuple[dict[str, Any], ...] = ()
    memories: tuple[dict[str, Any], ...] = ()
    goals: tuple[dict[str, Any], ...] = ()
    summary: str = ""
    query_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "entities": list(self.entities),
            "relationships": list(self.relationships),
            "memories": list(self.memories),
            "goals": list(self.goals),
            "summary": self.summary,
            "query_text": self.query_text,
        }

    def to_planner_snippets(self) -> list[str]:
        snippets: list[str] = []
        if self.summary:
            snippets.append(f"[world_model]\n{self.summary}")
        for entity in self.entities[:8]:
            label = entity.get("label") or entity.get("id") or "entity"
            etype = entity.get("type") or "node"
            snippets.append(f"[entity:{etype}:{label}]")
        for memory in self.memories[:5]:
            snippets.append(
                f"[memory:{memory.get('label', '')}]\n{memory.get('content', '')}"
            )
        for goal in self.goals[:5]:
            snippets.append(f"[goal:{goal.get('status', '')}] {goal.get('title', '')}")
        return snippets

    @classmethod
    def empty(cls, *, workspace_id: str = "", query_text: str = "") -> StateContext:
        return cls(workspace_id=workspace_id, query_text=query_text)
