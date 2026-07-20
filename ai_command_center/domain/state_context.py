"""State context projection — World Model as decision input."""

from __future__ import annotations

from dataclasses import dataclass
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

    def to_planner_snippets(self, *, max_tokens: int = 4096) -> list[str]:
        """Budget-aware snippets (priority: goal → workspace → entities → memories → rels)."""
        from ai_command_center.core.state_intelligence.projection_budget_manager import (
            ProjectionBudgetManager,
        )

        budget = ProjectionBudgetManager(max_tokens=max_tokens)
        goal_lines = [
            f"[goal:{g.get('status', '')}] {g.get('title', '')}" for g in self.goals
        ]
        if self.query_text:
            goal_lines.insert(0, f"[user_request]\n{self.query_text}")
        workspace_lines: list[str] = []
        if self.workspace_id:
            workspace_lines.append(f"[workspace]\n{self.workspace_id}")
        if self.summary:
            workspace_lines.append(f"[world_model]\n{self.summary}")
        recent_lines = [
            f"[recent:{e.get('type')}] {e.get('label', '')}"
            for e in self.entities
            if e.get("type") in {"execution_run", "execution_intent"}
        ]
        entity_lines = [
            f"[entity:{e.get('type') or 'node'}:{e.get('label') or e.get('id') or 'entity'}]"
            for e in self.entities
            if e.get("type") not in {"execution_run", "execution_intent", "workspace"}
        ]
        memory_lines = [
            f"[memory:{m.get('label', '')}]\n{m.get('content', '')}" for m in self.memories
        ]
        rel_lines = [
            f"[rel:{r.get('type', '')}] {r.get('from_node_id', '')}->{r.get('to_node_id', '')}"
            for r in self.relationships
        ]
        return budget.allocate_dict(
            {
                "goal": goal_lines,
                "workspace": workspace_lines,
                "recent_activity": recent_lines,
                "entities": entity_lines,
                "memories": memory_lines,
                "relationships": rel_lines,
            }
        )

    @classmethod
    def empty(cls, *, workspace_id: str = "", query_text: str = "") -> StateContext:
        return cls(workspace_id=workspace_id, query_text=query_text)
