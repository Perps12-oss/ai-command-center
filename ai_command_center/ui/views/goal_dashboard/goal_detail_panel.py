"""Goal Detail — read-only projection of the selected goal."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import GoalSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import goal_state_color
from ai_command_center.ui.views.goal_dashboard.goal_sorting import normalize_goal_status
from ai_command_center.ui.views.surface_state import article18_empty
from ai_command_center.ui.widget_utils import clear_children


class GoalDetailPanel(ctk.CTkFrame):
    """Displays description, status, priority, error, and metadata."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.GOAL_AMBER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Goal Detail",
            font=T.FONT_HEADER,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(side="left")
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(self, goal: GoalSnapshot | None) -> None:
        clear_children(self._body)
        if goal is None:
            ctk.CTkLabel(
                self._body,
                text=article18_empty(
                    why="No goal is selected for inspection.",
                    creates="Selecting a row in Goal List focuses detail on that projection.",
                    next_action="Select a goal, or submit a New Goal from the Hero.",
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=12)
            return
        status = normalize_goal_status(goal.status)
        fg, _ = goal_state_color(status)
        self._row("Goal ID", goal.goal_id or "—")
        self._row("Title", goal.text or "—")
        self._row("Status", status, color=fg)
        self._row("Priority", str(goal.priority))
        error = (goal.error or "").strip()
        self._row(
            "Error",
            error or "none",
            color=T.STATUS_ERROR if error else T.TEXT_MUTED,
        )
        meta = ", ".join(f"{k}={v}" for k, v in goal.meta) if goal.meta else "—"
        self._row("Metadata", meta, color=T.TEXT_SECONDARY)

    def _row(self, label: str, value: str, *, color: str = T.TEXT_PRIMARY) -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(
            frame,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=100,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            frame,
            text=value,
            font=T.FONT_SMALL,
            text_color=color,
            anchor="w",
            wraplength=260,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
