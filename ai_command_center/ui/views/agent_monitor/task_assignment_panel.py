"""Task Assignment — read-only visibility of projected agent tasks."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.agent_pipeline_snapshot import AgentPipelineSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class TaskAssignmentPanel(ctk.CTkFrame):
    """Read-only mapping of agent role to assigned task (no reassignment)."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.AGENT_PURPLE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Task Assignment",
            font=T.FONT_HEADER,
            text_color=T.AGENT_PURPLE,
            anchor="w",
        ).pack(side="left")
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(
        self,
        pipeline: AgentPipelineSnapshot,
        *,
        selected_agent_id: str = "",
    ) -> None:
        clear_children(self._body)
        runs = list(pipeline.runs)
        if selected_agent_id:
            selected = [r for r in runs if r.agent_id == selected_agent_id]
            if selected:
                runs = selected
        if not runs:
            ctk.CTkLabel(
                self._body,
                text=(
                    "No task assignments in the current projection.\n"
                    "Assignments appear when agent runs are spawned with tasks.\n"
                    "Next: start an agent pipeline that assigns work."
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=12)
            return

        parent = pipeline.pipeline_id or "—"
        for run in runs:
            card = ctk.CTkFrame(
                self._body,
                fg_color=T.BG_GLASS,
                border_color=T.BG_GLASS_BORDER,
                border_width=1,
                corner_radius=T.SMALL_RADIUS,
            )
            card.pack(fill="x", pady=3)
            self._line(card, "Assigned Task", run.task or "—")
            self._line(card, "Agent Role", run.spawn_role or "—")
            self._line(card, "Request ID", run.request_id or "—")
            self._line(card, "Parent Pipeline", parent)

    def _line(self, parent: Any, label: str, value: str) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=1)
        ctk.CTkLabel(
            row,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=120,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            row,
            text=value,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=260,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
