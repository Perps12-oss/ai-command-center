"""Automation catalog cards (Activepieces-style)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.automation_workspace import AutomationCatalogItem
from ai_command_center.ui.design_system import theme_v2 as T


class AutomationCatalog(ctk.CTkFrame):
    """Grid of automation cards with run actions."""

    def __init__(
        self,
        master: Any,
        *,
        on_run: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._on_run = on_run or (lambda _workflow_id: None)
        ctk.CTkLabel(
            self,
            text="AUTOMATIONS",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)

    def update(self, items: Sequence[AutomationCatalogItem]) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        if not items:
            ctk.CTkLabel(
                self._scroll,
                text="No automations",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(anchor="w", pady=8)
            return
        for item in items:
            card = ctk.CTkFrame(
                self._scroll,
                fg_color=T.BG_GLASS,
                corner_radius=T.CORNER_RADIUS,
                border_width=1,
                border_color=T.BG_GLASS_BORDER,
            )
            card.pack(fill="x", pady=4)
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                header,
                text=item.title,
                font=(T.FONT_FAMILY, 11, "bold"),
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                header,
                text=item.category,
                font=(T.FONT_FAMILY, 9),
                text_color=T.ACCENT_DEFAULT,
            ).pack(side="right")
            ctk.CTkLabel(
                card,
                text=item.description,
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                wraplength=260,
                justify="left",
            ).pack(fill="x", padx=10, pady=(0, 6))
            ctk.CTkButton(
                card,
                text="Run",
                width=64,
                height=24,
                font=(T.FONT_FAMILY, 10),
                fg_color=T.ACCENT_DEFAULT,
                hover_color=T.ACCENT_HOVER,
                command=lambda wf=item.workflow_id: self._on_run(wf),
                state="normal" if item.enabled else "disabled",
            ).pack(anchor="e", padx=10, pady=(0, 8))


__all__ = ["AutomationCatalog"]
