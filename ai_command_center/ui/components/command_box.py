"""Universal command input."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class CommandBox(ctk.CTkFrame):
    def __init__(self, master, on_submit, on_help=None, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_submit = on_submit
        self._on_help = on_help

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        self._entry = ctk.CTkEntry(
            row,
            placeholder_text="Chat, note:, remember:, > shell, go settings — type ? for help",
            height=40,
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_width=1,
            border_color=T.GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<Return>", self._submit)

        if on_help is not None:
            ctk.CTkButton(
                row,
                text="?",
                width=36,
                height=40,
                font=T.FONT_BODY,
                command=on_help,
            ).pack(side="right", padx=(8, 0))

    def _submit(self, _event=None) -> None:
        text = self._entry.get().strip()
        if text:
            self._on_submit(text)
        self._entry.delete(0, "end")

    def focus(self) -> None:
        self._entry.focus_set()
