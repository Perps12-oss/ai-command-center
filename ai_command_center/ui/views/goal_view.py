"""Goal dashboard — real AppState projection, no placeholder."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import PlanSnapshot
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import goal_state_color


class GoalView(ctk.CTkFrame):
    """Displays recent goals and the planner's last plan."""

    def __init__(
        self,
        master,
        on_command: Callable[[str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_command = on_command
        self._on_navigate = on_navigate
        self._build()

    def _build(self) -> None:
        # Active goals
        goals_card = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        goals_card.pack(fill="both", expand=True, padx=T.PAD, pady=(T.PAD, 8))

        ctk.CTkLabel(
            goals_card,
            text="Goals",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._goals_list = ctk.CTkFrame(goals_card, fg_color="transparent")
        self._goals_list.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        self._goal_rows: list[ctk.CTkLabel] = []
        for _ in range(10):
            lbl = ctk.CTkLabel(
                self._goals_list,
                text="",
                font=T.FONT_BODY,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                justify="left",
            )
            lbl.pack(fill="x", pady=(0, 2))
            self._goal_rows.append(lbl)

        # Plan
        plan_card = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        plan_card.pack(fill="x", padx=T.PAD, pady=(8, T.PAD))

        ctk.CTkLabel(
            plan_card,
            text="Last Plan",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._plan_goal = ctk.CTkLabel(
            plan_card,
            text="No plan generated yet",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._plan_goal.pack(fill="x", padx=T.PAD, pady=(0, 4))

        self._plan_steps = ctk.CTkFrame(plan_card, fg_color="transparent")
        self._plan_steps.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        self._plan_step_labels: list[ctk.CTkLabel] = []
        for _ in range(10):
            lbl = ctk.CTkLabel(
                self._plan_steps,
                text="",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            )
            lbl.pack(fill="x", pady=(0, 1))
            self._plan_step_labels.append(lbl)

    def apply_state(self, snap: Any) -> None:
        """Project brain goals and planner plan into the view."""
        brain_state = getattr(snap, "brain_state", None)
        goals = list(getattr(brain_state, "recent_goals", ()) if brain_state else ())

        for i, lbl in enumerate(self._goal_rows):
            if i < len(goals):
                g = goals[i]
                text = getattr(g, "text", "")
                status = getattr(g, "status", "")
                fg = goal_state_color(status)[0] if status else T.TEXT_SECONDARY
                lbl.configure(text=f"{status.title()}: {text}" if text else "Untitled goal", text_color=fg)
            else:
                lbl.configure(text="", text_color=T.TEXT_SECONDARY)

        raw_plan = getattr(snap, "planner_last_plan", None) or {}
        plan = PlanSnapshot.from_dict(raw_plan) if isinstance(raw_plan, dict) else PlanSnapshot()
        if plan.goal or plan.steps:
            self._plan_goal.configure(
                text=f"{plan.goal} ({plan.status})",
                text_color=T.TEXT_PRIMARY,
            )
            for i, lbl in enumerate(self._plan_step_labels):
                if i < len(plan.steps):
                    step = plan.steps[i]
                    lbl.configure(text=f"{i + 1}. {step.description} ({step.status})")
                else:
                    lbl.configure(text="")
        else:
            self._plan_goal.configure(text="No plan generated yet", text_color=T.TEXT_SECONDARY)
            for lbl in self._plan_step_labels:
                lbl.configure(text="")
