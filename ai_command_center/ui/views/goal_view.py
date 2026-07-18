"""Goal Dashboard workspace — Article 16 operational surface (Phase 11F).

Architecture contract:
- Pure renderer. Reads AppState via apply_state(snapshot) only.
- Uses AppState.brain_state (+ optional planner_last_plan compose).
- New Goal publishes GOAL_SUBMIT_REQUEST only (never lifecycle facts).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.brain_state_snapshot import GoalSnapshot
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.goal_dashboard import (
    GoalDetailPanel,
    GoalHistoryPanel,
    GoalListPanel,
    GoalProgressPanel,
    PlanPreviewPanel,
)
from ai_command_center.ui.views.goal_dashboard.goal_sorting import (
    count_by_bucket,
    highest_priority_active,
    resolve_plan,
)
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    domain_error_from_snap,
    set_surface_state,
)


class GoalView(ctk.CTkFrame):
    """Goal Dashboard orchestration shell (Hero + five Article 16 panels)."""

    def __init__(
        self,
        master: Any,
        *,
        on_new_goal: Callable[[str, int], None] | None = None,
        on_select: Callable[[str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        on_command: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_new_goal = on_new_goal
        self._on_select = on_select or (lambda _gid: None)
        self._on_navigate = on_navigate
        self._on_command = on_command
        self._selected_goal_id = ""
        self._last_snap: AppState | None = None
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GOAL_AMBER)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            top,
            text="Goal Dashboard",
            font=T.FONT_TITLE,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(side="left")
        self._metrics = ctk.CTkLabel(
            top,
            text="0 active · 0 queued · 0 paused · 0 failed",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._metrics.pack(side="right")

        bottom = ctk.CTkFrame(self._hero, fg_color="transparent")
        bottom.pack(fill="x", padx=T.PAD, pady=(8, T.PAD))
        self._hero_hint = ctk.CTkLabel(
            bottom,
            text="No active goal — submit a New Goal to begin.",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._hero_hint.pack(side="left", fill="x", expand=True)
        self._hero_action = ctk.CTkButton(
            bottom,
            text="New Goal",
            font=T.FONT_BODY,
            fg_color=T.GOAL_AMBER,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            height=28,
            width=120,
            command=self._new_goal,
        )
        self._hero_action.pack(side="right", padx=(8, 0))

        self._surface_state = ctk.CTkLabel(
            self._hero,
            text="Loading…",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self._surface_state.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=3)
        body.grid_rowconfigure(1, weight=2)

        self._list = GoalListPanel(body, on_select=self._select)
        self._list.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._detail = GoalDetailPanel(right)
        self._detail.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self._progress = GoalProgressPanel(right)
        self._progress.grid(row=1, column=0, sticky="nsew")

        bottom_row = ctk.CTkFrame(body, fg_color="transparent")
        bottom_row.grid(row=1, column=0, columnspan=2, sticky="nsew")
        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_columnconfigure(1, weight=1)
        bottom_row.grid_rowconfigure(0, weight=1)

        self._plan = PlanPreviewPanel(bottom_row)
        self._plan.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._history = GoalHistoryPanel(bottom_row)
        self._history.grid(row=0, column=1, sticky="nsew")

    def apply_state(self, snapshot: AppState | Any | None) -> None:
        """Project AppState.brain_state into Hero + panels."""
        if snapshot is None:
            set_surface_state(
                self._surface_state,
                kind="loading",
                message=article18_loading(
                    status="Status: loading Goal Dashboard",
                    what="brain_state.recent_goals and plan projection",
                    next_action="Wait for AppState refresh; then click New Goal if empty.",
                ),
            )
            return
        if not isinstance(snapshot, AppState):
            return
        self._last_snap = snapshot
        brain = snapshot.brain_state
        goals = list(brain.recent_goals)
        counts = count_by_bucket(goals)
        self._metrics.configure(
            text=(
                f"{counts['active']} active · {counts['queued']} queued · "
                f"{counts['paused']} paused · {counts['failed']} failed"
            )
        )
        top = highest_priority_active(goals)
        if top is not None:
            self._hero_hint.configure(
                text=f"Highest priority active: {top.text or top.goal_id}"
            )
            if not self._selected_goal_id:
                self._selected_goal_id = top.goal_id
        else:
            self._hero_hint.configure(
                text="No active goal — submit a New Goal to begin."
            )

        err = domain_error_from_snap(snapshot, topic_prefixes=("goal.", "brain.", "plan."))
        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif not goals and not getattr(brain.last_plan, "steps", ()):
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="No goals or plans are present in the brain_state projection.",
                    creates="Goals appear when New Goal publishes GOAL_SUBMIT_REQUEST.",
                    next_action="Click New Goal to submit the first goal.",
                ),
            )
        else:
            set_surface_state(self._surface_state, kind="data")

        selected = self._resolve_selected(goals)
        plan = resolve_plan(brain, snapshot.planner_last_plan)
        self._list.apply_snapshot(goals, selected_goal_id=self._selected_goal_id)
        self._detail.apply_snapshot(selected)
        self._plan.apply_snapshot(plan)
        self._progress.apply_snapshot(plan)
        self._history.apply_snapshot(goals)

    def _resolve_selected(self, goals: list[GoalSnapshot]) -> GoalSnapshot | None:
        if self._selected_goal_id:
            for g in goals:
                if g.goal_id == self._selected_goal_id:
                    return g
        return highest_priority_active(goals) or (goals[0] if goals else None)

    def _select(self, goal_id: str) -> None:
        self._selected_goal_id = str(goal_id)
        self._on_select(self._selected_goal_id)
        if self._last_snap is not None:
            self.apply_state(self._last_snap)

    def _new_goal(self) -> None:
        if self._on_new_goal is None:
            return
        self._on_new_goal("New Goal", 0)
