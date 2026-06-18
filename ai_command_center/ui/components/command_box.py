"""Universal command input."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T


class CommandBox(ctk.CTkFrame):
    def __init__(self, master, on_submit, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_submit = on_submit

        self._entry = ctk.CTkEntry(
            self,
            placeholder_text="Ask anything, search notes, or type > for commands…",
            height=40,
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._entry.pack(fill="x", expand=True)
        self._entry.bind("<Return>", self._submit)

    def _submit(self, _event=None) -> None:
        text = self._entry.get().strip()
        if text:
            self._on_submit(text)
        self._entry.delete(0, "end")

    def focus(self) -> None:
        self._entry.focus_set()
