"""Automation template gallery."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.automation_workspace import AutomationTemplateItem
from ai_command_center.ui.design_system import theme_v2 as T


class TemplateGallery(ctk.CTkFrame):
    """Template cards for starting new automations."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, corner_radius=0, **kwargs)
        ctk.CTkLabel(
            self,
            text="TEMPLATES",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def update(self, templates: Sequence[AutomationTemplateItem]) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        for template in templates:
            card = ctk.CTkFrame(
                self._scroll,
                fg_color=T.BG_GLASS,
                corner_radius=T.SMALL_RADIUS,
                border_width=1,
                border_color=T.BG_GLASS_BORDER,
            )
            card.pack(fill="x", pady=3)
            ctk.CTkLabel(
                card,
                text=template.title,
                font=(T.FONT_FAMILY, 10, "bold"),
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(6, 2))
            ctk.CTkLabel(
                card,
                text=template.description,
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                wraplength=240,
                justify="left",
            ).pack(fill="x", padx=10, pady=(0, 2))
            ctk.CTkLabel(
                card,
                text=f"{template.category} · {template.step_count} steps",
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 8))


__all__ = ["TemplateGallery"]
