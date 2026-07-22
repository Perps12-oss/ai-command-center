"""Brain Inspector workspace — projects AppState.brain_state."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.brain_state_snapshot import BrainStateSnapshot
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.brain import (
    ActionCard,
    GoalCard,
    ObservationCard,
    PlanCard,
)
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class BrainView(ctk.CTkFrame):
    """Operational brain surface: kernel, goals, observations, actions, plan."""

    def __init__(
        self,
        master: Any,
        *,
        on_select_goal: Callable[[str], None] | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_select_goal = on_select_goal
        self._on_inspect_select = on_inspect_select
        self._on_navigate = on_navigate
        self._build()

    def _build(self) -> None:
        hero = GlassCard(self, fg_color=T.BG_PANEL)
        hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        top = ctk.CTkFrame(hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        ctk.CTkLabel(
            top,
            text="Brain Inspector",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left")
        self._kernel_lbl = ctk.CTkLabel(
            top,
            text="kernel: —",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._kernel_lbl.pack(side="right")

        self._hint = ctk.CTkLabel(
            hero,
            text="Waiting for BrainStateSnapshot…",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._hint.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        if self._on_navigate is not None:
            ctk.CTkButton(
                hero,
                text="Open Goal Dashboard",
                width=160,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.GOAL_AMBER,
                hover_color=T.ACCENT_HOVER,
                text_color=T.TEXT_PRIMARY,
                command=lambda: self._on_navigate("goals"),
            ).pack(anchor="e", padx=T.PAD, pady=(0, T.PAD))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self._goals_scroll = self._section(body, "Goals", 0, 0)
        self._obs_scroll = self._section(body, "Observations", 0, 1)
        self._actions_scroll = self._section(body, "Runtime actions", 1, 0)
        self._plan_host = self._section(body, "Current plan", 1, 1)

    def _section(self, parent: Any, title: str, row: int, col: int) -> ctk.CTkScrollableFrame:
        frame = ctk.CTkFrame(parent, fg_color=T.BG_PANEL, corner_radius=T.CARD_RADIUS)
        frame.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        ctk.CTkLabel(
            frame,
            text=title,
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(10, 4))
        scroll = ctk.CTkScrollableFrame(frame, fg_color=T.BG_DEEP, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        return scroll

    def apply_state(self, snap: AppState) -> None:
        brain = getattr(snap, "brain_state", None) or BrainStateSnapshot()
        self._kernel_lbl.configure(text=f"kernel: {brain.kernel_state or 'unknown'}")
        active = next((g for g in brain.recent_goals if g.status in {"active", "running", "in_progress"}), None)
        if active is None and brain.recent_goals:
            active = brain.recent_goals[0]
        if active:
            self._hint.configure(text=f"Active goal: {active.text or active.goal_id}")
        elif brain.last_plan.goal:
            self._hint.configure(text=f"Plan goal: {brain.last_plan.goal}")
        else:
            self._hint.configure(
                text="No active goal — kernel is projecting an empty operational state."
            )

        clear_children(self._goals_scroll)
        if not brain.recent_goals:
            self._empty(self._goals_scroll, "No goals in brain_state yet.")
        else:
            for goal in brain.recent_goals[:20]:
                GoalCard(
                    self._goals_scroll,
                    goal_id=goal.goal_id,
                    text=goal.text,
                    status=goal.status,
                    priority=goal.priority,
                    on_select=self._select_goal,
                ).pack(fill="x", pady=3)

        clear_children(self._obs_scroll)
        if not brain.recent_observations:
            self._empty(self._obs_scroll, "No observations yet.")
        else:
            for obs in brain.recent_observations[:20]:
                ObservationCard(
                    self._obs_scroll,
                    content=obs.content,
                    source=obs.source,
                    confidence=obs.confidence,
                    on_select=lambda o=obs: self._inspect(
                        "observation",
                        o.observation_id or "obs",
                        o.content,
                        (("source", o.source), ("confidence", str(o.confidence))),
                    ),
                ).pack(fill="x", pady=3)

        clear_children(self._actions_scroll)
        if not brain.recent_runtime_actions:
            self._empty(self._actions_scroll, "No runtime actions yet.")
        else:
            for action in brain.recent_runtime_actions[:20]:
                ActionCard(
                    self._actions_scroll,
                    action_type=action.action_type,
                    status=action.status,
                    result=action.result,
                    error=action.error,
                    on_select=lambda a=action: self._inspect(
                        "execution_event",
                        a.action_id or "action",
                        a.action_type,
                        (("status", a.status), ("result", a.result), ("error", a.error)),
                    ),
                ).pack(fill="x", pady=3)

        clear_children(self._plan_host)
        plan = brain.last_plan
        steps = tuple((s.description or s.step_id, s.status) for s in plan.steps)
        if not plan.plan_id and not plan.goal and not steps:
            self._empty(self._plan_host, "No current plan.")
        else:
            PlanCard(
                self._plan_host,
                plan_id=plan.plan_id,
                goal=plan.goal,
                status=plan.status,
                steps=steps,
            ).pack(fill="x", pady=3)

    @staticmethod
    def _empty(parent: Any, message: str) -> None:
        ctk.CTkLabel(
            parent,
            text=message,
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=8, pady=12)

    def _select_goal(self, goal_id: str) -> None:
        if self._on_select_goal is not None:
            self._on_select_goal(goal_id)
        self._inspect("goal", goal_id, goal_id, ())

    def _inspect(
        self,
        kind: str,
        ref_id: str,
        label: str,
        payload: tuple[tuple[str, str], ...],
    ) -> None:
        if self._on_inspect_select is None:
            return
        self._on_inspect_select(
            InspectableRef(kind=kind, ref_id=ref_id or kind, label=label or kind, payload=payload)
        )


__all__ = ["BrainView"]
