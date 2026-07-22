"""Pipeline stage badge for Agent Operations (PR-UI-E09)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.agent_pipeline_snapshot import AgentPipelineSnapshot
from ai_command_center.ui.design_system import theme_v2 as T


class PipelineStage(ctk.CTkFrame):
    """Shows current pipeline id, stage, and planned tool count."""

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
            text="Pipeline Stage",
            font=T.FONT_HEADER,
            text_color=T.AGENT_PURPLE,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._stage = ctk.CTkLabel(
            self,
            text="stage: —",
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._stage.pack(fill="x", padx=T.PAD, pady=(0, 2))
        self._meta = ctk.CTkLabel(
            self,
            text="No pipeline projected",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._meta.pack(fill="x", padx=T.PAD, pady=(0, 10))

    def apply_snapshot(self, pipeline: AgentPipelineSnapshot) -> None:
        stage = pipeline.pipeline_stage or "—"
        self._stage.configure(text=f"stage: {stage}")
        if pipeline.pipeline_id:
            tools = len(pipeline.planned_tools)
            self._meta.configure(
                text=f"{pipeline.pipeline_id} · {tools} planned tools · "
                f"{len(pipeline.active_runs)} active"
            )
        else:
            self._meta.configure(text="No active pipeline id")


__all__ = ["PipelineStage"]
