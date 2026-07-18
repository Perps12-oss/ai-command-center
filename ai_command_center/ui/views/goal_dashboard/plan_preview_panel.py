"""Plan Preview — brain_state.last_plan / planner_last_plan compose."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import PlanSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color
from ai_command_center.ui.views.surface_state import article18_empty
from ai_command_center.ui.widget_utils import clear_children


class PlanPreviewPanel(ctk.CTkFrame):
    """Ordered plan steps without raw JSON."""

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
            text="Plan Preview",
            font=T.FONT_HEADER,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(side="left")
        self._goal = ctk.CTkLabel(
            self,
            text="No plan projected",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._goal.pack(fill="x", padx=T.PAD, pady=(0, 4))
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, height=90, border_width=0
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(self, plan: PlanSnapshot) -> None:
        clear_children(self._body)
        if not plan.goal and not plan.steps:
            self._goal.configure(text="No plan projected", text_color=T.TEXT_MUTED)
            ctk.CTkLabel(
                self._body,
                text=article18_empty(
                    why="No plan is present in brain_state.last_plan or planner_last_plan.",
                    creates="Plans appear after the planner generates steps for an active goal.",
                    next_action="Submit a New Goal so the scheduler can request a plan.",
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=8)
            return
        self._goal.configure(
            text=f"{plan.goal or '—'} · {plan.status or 'pending'}",
            text_color=T.TEXT_PRIMARY,
        )
        for i, step in enumerate(plan.steps):
            fg = status_color(step.status)
            ctk.CTkLabel(
                self._body,
                text=f"{i + 1}. {step.description or step.step_id or '—'} ({step.status})",
                font=T.FONT_SMALL,
                text_color=fg,
                anchor="w",
            ).pack(fill="x", padx=4, pady=1)
