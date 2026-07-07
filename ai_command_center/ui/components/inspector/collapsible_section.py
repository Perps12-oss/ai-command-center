"""Collapsible section primitive for inspector panels."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class CollapsibleSection(ctk.CTkFrame):
    """Expandable section with a title row and a packable body frame."""

    def __init__(self, master: Any, *, title: str, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._expanded = True

        self._header = ctk.CTkFrame(self, fg_color=T.BG_GLASS, corner_radius=0, height=32)
        self._header.pack(fill="x")
        self._header.pack_propagate(False)
        self._header.bind("<Button-1>", self._toggle_from_event, add="+")

        self._toggle_btn = ctk.CTkButton(
            self._header,
            text="▾",
            width=24,
            height=22,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self.toggle,
        )
        self._toggle_btn.pack(side="right", padx=8, pady=4)

        self._title_label = ctk.CTkLabel(
            self._header,
            text=title,
            font=(T.FONT_FAMILY, 10, "bold"),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._title_label.pack(side="left", padx=10, pady=7, fill="x", expand=True)
        self._title_label.bind("<Button-1>", self._toggle_from_event, add="+")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

    def set_title(self, text: str) -> None:
        self._title_label.configure(text=text)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = bool(expanded)
        if self._expanded:
            if not self.body.winfo_ismapped():
                self.body.pack(fill="both", expand=True)
            self._toggle_btn.configure(text="▾")
        else:
            if self.body.winfo_ismapped():
                self.body.pack_forget()
            self._toggle_btn.configure(text="▸")

    def toggle(self) -> bool:
        self.set_expanded(not self._expanded)
        return self._expanded

    def _toggle_from_event(self, _event: Any) -> None:
        self.toggle()


__all__ = ["CollapsibleSection"]
