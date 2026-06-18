"""Translucent panel with border — glassmorphism lite."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T


class GlassCard(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            **kwargs,
        )
