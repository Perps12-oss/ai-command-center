"""Goal List — primary Goal Dashboard surface."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.brain_state_snapshot import GoalSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import goal_state_color
from ai_command_center.ui.views.goal_dashboard.goal_sorting import (
    FILTER_OPTIONS,
    filter_goals,
    normalize_goal_status,
    sort_goals,
)
from ai_command_center.ui.views.surface_state import article18_empty
from ai_command_center.ui.widget_utils import clear_children


def _format_date(ts: float) -> str:
    if not ts:
        return "—"
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(ts)))
    except Exception:
        return "—"


class GoalListPanel(ctk.CTkFrame):
    """Browse projected goals with status filter and operator sort."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.GOAL_AMBER,
            border_width=2,
            corner_radius=T.CORNER_RADIUS,
        )
        self._on_select = on_select
        self._goals: list[GoalSnapshot] = []
        self._selected_id = ""
        self._filter = "all"

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(12, 4))
        ctk.CTkLabel(
            header,
            text="Goal List",
            font=T.FONT_TITLE,
            text_color=T.GOAL_AMBER,
            anchor="w",
        ).pack(side="left")
        self._count = ctk.CTkLabel(
            header,
            text="0 goals",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._count.pack(side="right")

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", padx=T.PAD, pady=(0, 6))
        self._filter_menu = ctk.CTkOptionMenu(
            filters,
            values=list(FILTER_OPTIONS),
            width=120,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.GOAL_AMBER,
            command=self._on_filter,
        )
        self._filter_menu.set("all")
        self._filter_menu.pack(side="left")

        self._list = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 10))

    def apply_snapshot(
        self,
        goals: list[GoalSnapshot] | tuple[GoalSnapshot, ...],
        *,
        selected_goal_id: str = "",
    ) -> None:
        self._goals = list(goals)
        self._selected_id = selected_goal_id
        self._render()

    def _on_filter(self, value: str) -> None:
        self._filter = str(value or "all")
        self._render()

    def _render(self) -> None:
        rows = sort_goals(filter_goals(self._goals, self._filter))
        self._count.configure(text=f"{len(rows)} goals")
        clear_children(self._list)
        if not rows:
            ctk.CTkLabel(
                self._list,
                text=article18_empty(
                    why="No goals match the current filter in the brain projection.",
                    creates="Goals appear when a GOAL_SUBMIT_REQUEST is accepted by the scheduler.",
                    next_action="Click New Goal in the Hero, or clear the status filter.",
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=12)
            return
        for goal in rows:
            self._add_row(goal)

    def _add_row(self, goal: GoalSnapshot) -> None:
        selected = goal.goal_id == self._selected_id
        status = normalize_goal_status(goal.status)
        fg, _ = goal_state_color(status)
        row = ctk.CTkFrame(
            self._list,
            fg_color=T.BG_GLASS if selected else "transparent",
            border_color=T.GOAL_AMBER if selected else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        row.pack(fill="x", pady=2)
        title = goal.text or goal.goal_id or "Untitled goal"
        ctk.CTkLabel(
            row,
            text=f"{title} · P{goal.priority} · {status} · {_format_date(goal.updated_at or goal.created_at)}",
            font=T.FONT_SMALL,
            text_color=fg,
            anchor="w",
        ).pack(fill="x", padx=8, pady=6)
        gid = goal.goal_id

        def _select(_e: Any = None, _gid: str = gid) -> None:
            if self._on_select:
                self._on_select(_gid)

        row.bind("<Button-1>", _select)
