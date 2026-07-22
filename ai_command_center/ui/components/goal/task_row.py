"""Plan/task row for the Goal Workspace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color


class TaskRow(ctk.CTkFrame):
    """Single plan step presented as a selectable task."""

    def __init__(
        self,
        master: Any,
        *,
        step_id: str,
        description: str,
        status: str,
        index: int = 0,
        selected: bool = False,
        on_select: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.HERO_CYAN_DIM if selected else T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        self._step_id = step_id
        self._on_select = on_select
        color = status_color(status)
        ctk.CTkLabel(
            self,
            text=f"{index + 1}. {description or step_id or 'task'}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=360,
        ).pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            self,
            text=status or "pending",
            font=(T.FONT_FAMILY, 10),
            text_color=color,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 8))
        self.bind("<Button-1>", self._click)

    def _click(self, _e: Any = None) -> None:
        if self._on_select is not None and self._step_id:
            self._on_select(self._step_id)


__all__ = ["TaskRow"]
