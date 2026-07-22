"""Agent run timeline — TimelineRenderer composition (no new timeline engine)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.agent_pipeline_snapshot import (
    AgentPipelineSnapshot,
    AgentRunSnapshot,
)
from ai_command_center.ui.components.timeline_renderer import TimelineRenderer
from ai_command_center.ui.design_system import theme_v2 as T


def planned_tool_steps(
    pipeline: AgentPipelineSnapshot,
    *,
    run: AgentRunSnapshot | None = None,
) -> list[dict[str, object]]:
    """Project planned tools (and optional run steps) into TimelineRenderer tiles."""
    steps: list[dict[str, object]] = []
    tools = list(pipeline.planned_tools)
    if not tools and run is not None and run.steps > 0:
        for index in range(run.steps):
            steps.append(
                {
                    "name": f"step {index + 1}",
                    "status": "completed" if run.is_terminal else "running",
                    "duration_ms": 0,
                }
            )
        return steps
    completed = sum(1 for r in pipeline.runs if r.is_terminal and not r.error)
    for index, tool in enumerate(tools):
        if index < completed:
            status = "completed"
        elif index == completed and pipeline.pipeline_active:
            status = "running"
        else:
            status = "pending"
        steps.append({"name": str(tool), "status": status, "duration_ms": 0})
    return steps


class RunTimeline(ctk.CTkFrame):
    """Horizontal run/tool timeline using shared TimelineRenderer."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.AGENT_PURPLE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text="Run Timeline",
            font=T.FONT_HEADER,
            text_color=T.AGENT_PURPLE,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._renderer = TimelineRenderer(self)
        self._renderer.pack(fill="x", padx=8, pady=(0, 8))

    def apply_snapshot(
        self,
        pipeline: AgentPipelineSnapshot,
        *,
        selected_agent_id: str = "",
    ) -> None:
        run = pipeline.run_by_id(selected_agent_id) if selected_agent_id else pipeline.active_run
        steps = planned_tool_steps(pipeline, run=run)
        active_index = next(
            (i for i, step in enumerate(steps) if step.get("status") == "running"),
            -1,
        )
        self._renderer.render(steps, active_index=active_index)


__all__ = ["RunTimeline", "planned_tool_steps"]
