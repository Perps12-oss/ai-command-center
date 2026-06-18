"""Navigation sidebar."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T

NAV_ITEMS: tuple[tuple[str, str], ...] = (
    ("home", "Home"),
    ("chat", "Chat"),
    ("notes", "Notes"),
    ("system", "System"),
    ("plugins", "Plugins"),
    ("settings", "Settings"),
)


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, **kwargs) -> None:
        super().__init__(
            master,
            width=T.SIDEBAR_WIDTH,
            fg_color=T.BG_PANEL,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._active = "home"

        ctk.CTkLabel(
            self,
            text="Command Center",
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 8))

        for view_id, label in NAV_ITEMS:
            btn = ctk.CTkButton(
                self,
                text=label,
                anchor="w",
                font=T.FONT_BODY,
                fg_color="transparent",
                text_color=T.TEXT_SECONDARY,
                hover_color=T.BG_GLASS,
                height=36,
                command=lambda v=view_id: self._select(v, on_navigate),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._buttons[view_id] = btn

        self._highlight()

    def _select(self, view_id: str, on_navigate) -> None:
        self._active = view_id
        self._highlight()
        on_navigate(view_id)

    def _highlight(self) -> None:
        for vid, btn in self._buttons.items():
            if vid == self._active:
                btn.configure(fg_color=T.BG_GLASS, text_color=T.TEXT_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=T.TEXT_SECONDARY)

    def set_active(self, view_id: str) -> None:
        self._active = view_id
        self._highlight()
