"""Status components for the Workspace Design System."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system.colors import status_color
from ai_command_center.ui.design_system.theme_v2 import (
    BG_GLASS,
    BG_GLASS_BORDER,
    CORNER_RADIUS,
    FONT_ROLE,
    FONT_SMALL,
    PAD,
    TEXT_MUTED,
)


class StatusDot(ctk.CTkFrame):
    """Small coloured dot for status indication."""

    def __init__(self, master, state: str = "unknown", size: int = 8, **kwargs) -> None:
        super().__init__(
            master,
            width=size,
            height=size,
            fg_color=status_color(state),
            corner_radius=size // 2,
            **kwargs,
        )
        self.pack_propagate(False)


class StatusPill(ctk.CTkFrame):
    """Status pill with dot, label, and sub-label."""

    def __init__(
        self,
        master,
        title: str,
        state: str = "unknown",
        detail: str = "",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=BG_GLASS,
            border_color=BG_GLASS_BORDER,
            border_width=1,
            corner_radius=CORNER_RADIUS,
            **kwargs,
        )
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=(10, 2))

        StatusDot(top, state).pack(side="left")
        ctk.CTkLabel(
            top,
            text=title.upper(),
            font=FONT_ROLE,
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(6, 0))

        self._status = ctk.CTkLabel(
            self,
            text=detail or state,
            font=FONT_SMALL,
            text_color=status_color(state),
            anchor="w",
        )
        self._status.pack(fill="x", padx=PAD, pady=(0, 10))

    def update(self, state: str, detail: str = "") -> None:
        self._status.configure(text=detail or state, text_color=status_color(state))


class Badge(ctk.CTkFrame):
    """Small badge with text."""

    def __init__(self, master, text: str, color: str = "#22C55E", **kwargs) -> None:
        super().__init__(
            master,
            fg_color=f"{color}22",
            border_color=f"{color}44",
            border_width=1,
            corner_radius=T.PILL_RADIUS,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text=text,
            font=FONT_ROLE,
            text_color=color,
        ).pack(padx=10, pady=2)
