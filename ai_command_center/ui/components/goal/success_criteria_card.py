"""Success criteria card derived from goal meta / plan progress."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import GoalSnapshot, PlanSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class SuccessCriteriaCard(ctk.CTkFrame):
    """Shows success criteria and plan completion progress."""

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
            text="Success Criteria",
            font=T.FONT_HEADER,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(
        self,
        goal: GoalSnapshot | None,
        plan: PlanSnapshot | None = None,
    ) -> None:
        clear_children(self._body)
        criteria: list[str] = []
        if goal is not None:
            for key, value in goal.meta:
                if "criteria" in key.lower() or "success" in key.lower():
                    criteria.append(f"{key}: {value}")
            if goal.error:
                criteria.append(f"Must clear error: {goal.error}")
        if plan is not None and plan.steps:
            done = sum(
                1 for s in plan.steps if s.status.lower() in {"done", "complete", "completed"}
            )
            criteria.append(f"Plan steps complete: {done}/{len(plan.steps)}")
            if plan.status:
                criteria.append(f"Plan status: {plan.status}")
        if not criteria:
            ctk.CTkLabel(
                self._body,
                text="No explicit success criteria on this goal yet.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=4, pady=8)
            return
        for line in criteria:
            ctk.CTkLabel(
                self._body,
                text=f"• {line}",
                font=T.FONT_SMALL,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
                wraplength=360,
                justify="left",
            ).pack(fill="x", padx=4, pady=2)


__all__ = ["SuccessCriteriaCard"]
