"""Goal History — projected recent_goals feed only (no history service)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import GoalSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import goal_state_color
from ai_command_center.ui.views.goal_dashboard.goal_sorting import normalize_goal_status
from ai_command_center.ui.views.surface_state import article18_empty
from ai_command_center.ui.widget_utils import clear_children


class GoalHistoryPanel(ctk.CTkFrame):
    """Operational history from brain_state.recent_goals (N projected → N rows)."""

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
            text="Goal History",
            font=T.FONT_HEADER,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(side="left")
        self._count = ctk.CTkLabel(
            header,
            text="0",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._count.pack(side="right")
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(self, goals: list[GoalSnapshot] | tuple[GoalSnapshot, ...]) -> None:
        items = list(goals)
        self._count.configure(text=str(len(items)))
        clear_children(self._body)
        if not items:
            ctk.CTkLabel(
                self._body,
                text=article18_empty(
                    why="No goal history is present in the brain_state projection.",
                    creates="History grows as goals are submitted and their status changes.",
                    next_action="Submit a New Goal to begin recording projected history.",
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=12)
            return
        for goal in items:
            status = normalize_goal_status(goal.status)
            fg, _ = goal_state_color(status)
            row = ctk.CTkFrame(
                self._body,
                fg_color="transparent",
                border_color=T.BG_GLASS_BORDER,
                border_width=1,
                corner_radius=T.SMALL_RADIUS,
            )
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row,
                text=f"{status.upper()} · {goal.text or goal.goal_id or '—'} · P{goal.priority}",
                font=T.FONT_SMALL,
                text_color=fg,
                anchor="w",
            ).pack(fill="x", padx=8, pady=(4, 0))
            summary = (goal.error or "").strip() or "—"
            ctk.CTkLabel(
                row,
                text=f"id={goal.goal_id or '—'} · error={summary[:60]}",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=8, pady=(0, 4))
