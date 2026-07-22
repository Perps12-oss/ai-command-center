"""Selectable agent run card for Agent Operations (PR-UI-E09)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color


class AgentCard(ctk.CTkFrame):
    """Compact run summary card."""

    def __init__(
        self,
        master: Any,
        *,
        agent_id: str,
        role: str = "",
        state: str = "",
        task: str = "",
        selected: bool = False,
        on_select: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.HERO_CYAN_DIM if selected else T.BG_GLASS,
            border_color=T.AGENT_PURPLE if selected else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        self._agent_id = agent_id
        self._on_select = on_select
        color = status_color(state)
        title = role or agent_id
        ctk.CTkLabel(
            self,
            text=title,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            self,
            text=f"{state or 'unknown'}  ·  {agent_id}",
            font=T.FONT_SMALL,
            text_color=color,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 2))
        if task:
            ctk.CTkLabel(
                self,
                text=task[:80],
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                wraplength=280,
                justify="left",
            ).pack(fill="x", padx=10, pady=(0, 8))
        self.bind("<Button-1>", self._click)

    def _click(self, _e: Any = None) -> None:
        if self._on_select is not None and self._agent_id:
            self._on_select(self._agent_id)


__all__ = ["AgentCard"]
