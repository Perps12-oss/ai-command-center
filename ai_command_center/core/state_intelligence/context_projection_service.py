"""ContextProjectionService — graph state → planner context within budget."""

from __future__ import annotations

from typing import Any

from ai_command_center.domain.state_context import StateContext
from ai_command_center.services.base import BaseService
from ai_command_center.core.state_intelligence.projection_budget_manager import ProjectionBudgetManager
from ai_command_center.core.state_intelligence.world_model_query_service import WorldModelQueryService


class ContextProjectionService(BaseService):
    """Builds structured planner context from WorldModelQueryService."""

    name = "context_projection"

    def __init__(
        self,
        bus,
        query_service: WorldModelQueryService,
        *,
        budget_manager: ProjectionBudgetManager | None = None,
    ) -> None:
        super().__init__(bus)
        self._query = query_service
        self._budget = budget_manager or ProjectionBudgetManager()

    def _on_load(self) -> None:
        return

    def _on_unload(self) -> None:
        return

    def project(
        self,
        *,
        text: str = "",
        workspace_id: str = "",
        state_context: StateContext | None = None,
    ) -> StateContext:
        """Return a budgeted StateContext for the planner."""
        ctx = state_context or self._query.project_state(
            text=text,
            workspace_id=workspace_id,
        )
        snippets = self.build_snippets(ctx, user_request=text or ctx.query_text)
        summary = "\n".join(snippets) if snippets else ctx.summary
        return StateContext(
            workspace_id=ctx.workspace_id,
            entities=ctx.entities,
            relationships=ctx.relationships,
            memories=ctx.memories,
            goals=ctx.goals,
            summary=summary,
            query_text=ctx.query_text or text,
        )

    def build_snippets(
        self,
        ctx: StateContext,
        *,
        user_request: str = "",
    ) -> list[str]:
        """Convert state into budgeted planner snippets (not chat history)."""
        goal_lines: list[str] = []
        if user_request or ctx.query_text:
            goal_lines.append(f"[user_request]\n{user_request or ctx.query_text}")
        for goal in ctx.goals[:5]:
            goal_lines.append(
                f"[goal:{goal.get('status', '')}] {goal.get('title', '')}"
            )

        workspace_lines: list[str] = []
        if ctx.workspace_id:
            workspace_lines.append(f"[workspace]\n{ctx.workspace_id}")
        for entity in ctx.entities:
            if entity.get("type") == "workspace":
                workspace_lines.append(f"[workspace_entity]\n{entity.get('label', '')}")

        recent_lines: list[str] = []
        for entity in ctx.entities:
            if entity.get("type") in {"execution_run", "execution_intent"}:
                attrs = entity.get("attributes") or {}
                recent_lines.append(
                    f"[recent:{entity.get('type')}] {entity.get('label', '')} "
                    f"status={attrs.get('status', '')}"
                )

        entity_lines: list[str] = []
        for entity in ctx.entities:
            if entity.get("type") in {"execution_run", "execution_intent", "workspace"}:
                continue
            etype = entity.get("type") or "node"
            label = entity.get("label") or entity.get("id") or "entity"
            entity_lines.append(f"[entity:{etype}:{label}]")

        memory_lines: list[str] = []
        for memory in ctx.memories:
            memory_lines.append(
                f"[memory:{memory.get('label', '')}]\n{memory.get('content', '')}"
            )

        rel_lines: list[str] = []
        for rel in ctx.relationships:
            rel_lines.append(
                f"[rel:{rel.get('type', '')}] "
                f"{rel.get('from_node_id', '')}->{rel.get('to_node_id', '')} "
                f"status={rel.get('status', '')} conf={rel.get('confidence', '')}"
            )

        return self._budget.allocate_dict(
            {
                "goal": goal_lines,
                "workspace": workspace_lines,
                "recent_activity": recent_lines,
                "entities": entity_lines,
                "memories": memory_lines,
                "relationships": rel_lines,
            }
        )

    def budget_info(self) -> dict[str, Any]:
        return self._budget.to_dict()
