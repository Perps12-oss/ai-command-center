"""Surface / card components for the Workspace Design System."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system.theme_v2 import (
    BG_GLASS,
    BG_GLASS_BORDER,
    BG_PANEL,
    CARD_RADIUS,
    CORNER_RADIUS,
    PAD,
)


class Card(ctk.CTkFrame):
    """Standard dashboard card with glass border."""

    def __init__(self, master, *, title: str = "", **kwargs) -> None:
        super().__init__(
            master,
            fg_color=BG_GLASS,
            border_color=BG_GLASS_BORDER,
            border_width=1,
            corner_radius=CARD_RADIUS,
            **kwargs,
        )
        if title:
            ctk.CTkLabel(
                self,
                text=title,
                font=("Segoe UI", 13, "bold"),
                text_color="#F0F0F5",
                anchor="w",
            ).pack(anchor="w", padx=PAD, pady=(PAD, 4))


class Panel(ctk.CTkFrame):
    """Larger container with panel background."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=BG_PANEL,
            corner_radius=CORNER_RADIUS,
            **kwargs,
        )


class Section(ctk.CTkFrame):
    """Transparent section header with uppercase label."""

    def __init__(self, master, label: str, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=("Segoe UI", 10, "bold"),
            text_color="#6B6B80",
            anchor="w",
        ).pack(anchor="w")
