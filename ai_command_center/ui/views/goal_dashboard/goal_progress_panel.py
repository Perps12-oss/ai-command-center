"""Goal Progress — derived from projected plan step statuses only."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import PlanSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.surface_state import article18_empty


def plan_progress(plan: PlanSnapshot) -> tuple[int, int, float, str]:
    """Return (completed, total, fraction, label). Never invent percentages without steps."""
    steps = list(plan.steps)
    total = len(steps)
    if not total:
        return 0, 0, 0.0, "No plan projected"
    done = sum(
        1
        for s in steps
        if str(s.status).lower() in {"complete", "completed", "success", "done"}
    )
    fraction = done / total
    return done, total, fraction, f"{done}/{total} steps · {int(fraction * 100)}%"


class GoalProgressPanel(ctk.CTkFrame):
    """Visual progress from plan steps; explicit empty when no plan."""

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
            text="Goal Progress",
            font=T.FONT_HEADER,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(side="left")
        self._label = ctk.CTkLabel(
            self,
            text="No plan projected",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._label.pack(fill="x", padx=T.PAD, pady=(0, 6))
        self._track = ctk.CTkFrame(
            self,
            fg_color=T.BG_DEEP,
            height=16,
            corner_radius=T.SMALL_RADIUS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
        )
        self._track.pack(fill="x", padx=T.PAD, pady=(0, 6))
        self._track.pack_propagate(False)
        self._fill = ctk.CTkFrame(
            self._track,
            fg_color=T.GOAL_AMBER,
            height=14,
            corner_radius=T.SMALL_RADIUS,
            width=4,
        )
        self._fill.place(x=1, y=1, relheight=0.9, relwidth=0.02)
        self._empty = ctk.CTkLabel(
            self,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self._empty.pack(fill="x", padx=T.PAD, pady=(0, 10))

    def apply_snapshot(self, plan: PlanSnapshot) -> None:
        done, total, fraction, label = plan_progress(plan)
        if total == 0:
            self._label.configure(text="No plan projected", text_color=T.TEXT_MUTED)
            self._fill.place(x=1, y=1, relheight=0.9, relwidth=0.02)
            self._empty.configure(
                text=article18_empty(
                    why="Progress cannot be derived because no plan steps are projected.",
                    creates="Step completion appears after the planner emits a plan for an active goal.",
                    next_action="Submit a New Goal to start planning, then return here.",
                )
            )
            return
        self._label.configure(text=label, text_color=T.TEXT_PRIMARY)
        self._fill.place(x=1, y=1, relheight=0.9, relwidth=max(0.02, fraction))
        self._empty.configure(text=f"Plan status: {plan.status or 'pending'}")
