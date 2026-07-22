"""Operation card for Mission Control Operations (PR-UI-E11)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class OperationCard(ctk.CTkFrame):
    """Compact operation library entry."""

    def __init__(
        self,
        master: Any,
        *,
        correlation_id: str,
        title: str = "",
        status: str = "",
        selected: bool = False,
        on_select: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.HERO_CYAN_DIM if selected else T.BG_GLASS,
            border_color=T.EXECUTION_BLUE if selected else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        self._correlation_id = correlation_id
        self._on_select = on_select
        ctk.CTkLabel(
            self,
            text=title or correlation_id or "Operation",
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            self,
            text=f"{status or 'unknown'}  ·  {correlation_id}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 8))
        self.bind("<Button-1>", self._click)

    def _click(self, _e: Any = None) -> None:
        if self._on_select is not None and self._correlation_id:
            self._on_select(self._correlation_id)


__all__ = ["OperationCard"]
