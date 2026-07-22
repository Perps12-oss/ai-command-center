"""Goal detail panel for the Goal Workspace (E07)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import GoalSnapshot, PlanSnapshot
from ai_command_center.ui.components.goal.success_criteria_card import SuccessCriteriaCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import goal_state_color
from ai_command_center.ui.views.goal_dashboard.goal_sorting import normalize_goal_status
from ai_command_center.ui.views.surface_state import article18_empty
from ai_command_center.ui.widget_utils import clear_children


class GoalDetail(ctk.CTkFrame):
    """Selected goal fields plus success criteria composition."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.GOAL_AMBER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text="Goal Detail",
            font=T.FONT_HEADER,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._fields = ctk.CTkScrollableFrame(self, fg_color=T.BG_DEEP, height=120)
        self._fields.pack(fill="x", padx=8, pady=(0, 4))
        self._criteria = SuccessCriteriaCard(self)
        self._criteria.pack(fill="both", expand=True, padx=0, pady=(0, 0))

    def apply_snapshot(
        self,
        goal: GoalSnapshot | None,
        plan: PlanSnapshot | None = None,
    ) -> None:
        clear_children(self._fields)
        if goal is None:
            ctk.CTkLabel(
                self._fields,
                text=article18_empty(
                    why="No goal is selected for inspection.",
                    creates="Selecting a row in the Goal Tree focuses detail.",
                    next_action="Select a goal, or submit a New Goal from the Hero.",
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=8)
            self._criteria.apply_snapshot(None, plan)
            return
        status = normalize_goal_status(goal.status)
        fg, _ = goal_state_color(status)
        self._row("Goal ID", goal.goal_id or "—")
        self._row("Title", goal.text or "—")
        self._row("Status", status, color=fg)
        self._row("Priority", str(goal.priority))
        error = (goal.error or "").strip()
        self._row("Error", error or "none", color=T.STATUS_ERROR if error else T.TEXT_MUTED)
        self._criteria.apply_snapshot(goal, plan)

    def _row(self, label: str, value: str, *, color: str = T.TEXT_PRIMARY) -> None:
        frame = ctk.CTkFrame(self._fields, fg_color="transparent")
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


__all__ = ["GoalDetail"]
