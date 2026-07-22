"""Goal tree — goals grouped by operational status bucket."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import GoalSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import goal_state_color
from ai_command_center.ui.views.goal_dashboard.goal_sorting import normalize_goal_status
from ai_command_center.ui.widget_utils import clear_children

_BUCKET_ORDER = ("active", "queued", "paused", "failed", "completed", "cancelled", "other")


class GoalTree(ctk.CTkFrame):
    """Collapsible-style grouped goal list for the Goal Workspace."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.GOAL_AMBER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            **kwargs,
        )
        self._on_select = on_select
        ctk.CTkLabel(
            self,
            text="Goal Tree",
            font=T.FONT_HEADER,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._body = ctk.CTkScrollableFrame(self, fg_color=T.BG_DEEP, corner_radius=0)
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(
        self,
        goals: Sequence[GoalSnapshot],
        *,
        selected_goal_id: str = "",
    ) -> None:
        clear_children(self._body)
        if not goals:
            ctk.CTkLabel(
                self._body,
                text="No goals in the tree yet.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=8, pady=12)
            return

        buckets: dict[str, list[GoalSnapshot]] = {k: [] for k in _BUCKET_ORDER}
        for goal in goals:
            status = normalize_goal_status(goal.status)
            buckets.setdefault(status if status in buckets else "other", []).append(goal)

        for bucket in _BUCKET_ORDER:
            items = buckets.get(bucket) or []
            if not items:
                continue
            ctk.CTkLabel(
                self._body,
                text=bucket.upper(),
                font=T.FONT_ROLE,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=6, pady=(8, 2))
            for goal in items:
                selected = bool(selected_goal_id and goal.goal_id == selected_goal_id)
                fg, _ = goal_state_color(normalize_goal_status(goal.status))
                btn = ctk.CTkButton(
                    self._body,
                    text=f"{goal.text or goal.goal_id}  ·  p{goal.priority}",
                    anchor="w",
                    font=T.FONT_SMALL,
                    fg_color=T.HERO_CYAN_DIM if selected else T.BG_GLASS,
                    hover_color=T.LIGHT_GLASS,
                    text_color=fg if not selected else T.HERO_CYAN,
                    height=32,
                    command=lambda gid=goal.goal_id: self._select(gid),
                )
                btn.pack(fill="x", padx=4, pady=2)

    def _select(self, goal_id: str) -> None:
        if self._on_select is not None:
            self._on_select(goal_id)


__all__ = ["GoalTree"]
