"""Pipeline Progress — primary Agent Monitor visual (stage + tools)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.agent_pipeline_snapshot import AgentPipelineSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


def tool_progress_counts(pipeline: AgentPipelineSnapshot) -> tuple[int, int, int]:
    """Derive (planned, completed, remaining) from projected pipeline + runs."""
    planned = list(pipeline.planned_tools)
    planned_count = len(planned)
    completed = sum(
        1
        for r in pipeline.runs
        if str(r.state).lower() in {"terminated", "completed", "complete"}
        and not str(r.error or "").strip()
    )
    if planned_count:
        remaining = max(0, planned_count - completed)
    else:
        remaining = len([r for r in pipeline.runs if r.is_active])
    return planned_count, completed, remaining


class PipelineProgressPanel(ctk.CTkFrame):
    """Dominant operational surface: what agents are doing right now."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.AGENT_PURPLE,
            border_width=2,
            corner_radius=T.CORNER_RADIUS,
        )
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(12, 4))
        ctk.CTkLabel(
            header,
            text="Pipeline Progress",
            font=T.FONT_TITLE,
            text_color=T.AGENT_PURPLE,
            anchor="w",
        ).pack(side="left")
        self._stage = ctk.CTkLabel(
            header,
            text="No active pipeline",
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._stage.pack(side="right")

        self._counts = ctk.CTkLabel(
            self,
            text="Planned 0 · Completed 0 · Remaining 0",
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._counts.pack(fill="x", padx=T.PAD, pady=(4, 6))

        # Visual progress bar (theme tokens only — no hardcoded colors).
        self._track = ctk.CTkFrame(
            self,
            fg_color=T.BG_DEEP,
            height=18,
            corner_radius=T.SMALL_RADIUS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
        )
        self._track.pack(fill="x", padx=T.PAD, pady=(0, 8))
        self._track.pack_propagate(False)
        self._fill = ctk.CTkFrame(
            self._track,
            fg_color=T.AGENT_PURPLE,
            height=16,
            corner_radius=T.SMALL_RADIUS,
            width=4,
        )
        self._fill.place(x=1, y=1, relheight=0.9)

        self._tools = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, height=72, border_width=0
        )
        self._tools.pack(fill="both", expand=True, padx=8, pady=(0, 10))

    def apply_snapshot(self, pipeline: AgentPipelineSnapshot) -> None:
        stage = pipeline.pipeline_stage or ""
        if pipeline.pipeline_id and stage and stage != "complete":
            self._stage.configure(
                text=f"{pipeline.pipeline_id}: {stage}",
                text_color=T.AGENT_PURPLE,
            )
        elif stage == "complete":
            self._stage.configure(text="Pipeline complete", text_color=T.TEXT_SECONDARY)
        else:
            self._stage.configure(
                text="No active pipeline", text_color=T.TEXT_SECONDARY
            )

        planned_n, completed_n, remaining_n = tool_progress_counts(pipeline)
        self._counts.configure(
            text=(
                f"Planned {planned_n} · Completed {completed_n} · Remaining {remaining_n}"
            )
        )
        total = max(planned_n, completed_n + remaining_n, 1)
        fraction = min(1.0, completed_n / total) if total else 0.0
        # place(relwidth=...) drives the visual progress without raw JSON.
        self._fill.place(x=1, y=1, relheight=0.9, relwidth=max(0.02, fraction))

        clear_children(self._tools)
        tools = list(pipeline.planned_tools)
        if not tools:
            ctk.CTkLabel(
                self._tools,
                text=(
                    "No planned tools in the current projection.\n"
                    "Tool steps appear when a pipeline plans capabilities to run.\n"
                    "Next: start a pipeline that schedules tools."
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=8)
            return
        for idx, tool in enumerate(tools):
            done = idx < completed_n
            mark = "[done]" if done else "[ ]"
            color = T.STATUS_READY if done else T.TEXT_PRIMARY
            ctk.CTkLabel(
                self._tools,
                text=f"{mark}  {tool}",
                font=T.FONT_BODY,
                text_color=color,
                anchor="w",
            ).pack(fill="x", padx=4, pady=2)
