"""Translucent floating panel — subtle slate glass border, clean corners."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class GlassCard(ctk.CTkFrame):
    """Floating glass pane — 1px slate border, 16px radius, transparent children."""

    def __init__(self, master, **kwargs) -> None:
        corner = kwargs.pop("corner_radius", T.CARD_RADIUS)
        fg = kwargs.pop("fg_color", T.GLASS_BG)
        border_w = kwargs.pop("border_width", 1)
        border = kwargs.pop("border_color", T.GLASS_BORDER)
        if border_w == 0:
            border = fg

        super().__init__(
            master,
            fg_color=fg,
            border_color=border,
            border_width=border_w,
            corner_radius=corner,
            **kwargs,
        )
