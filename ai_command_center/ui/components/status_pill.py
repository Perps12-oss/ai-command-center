"""Status pill — connected / healthy / error."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_badge


class StatusPill(ctk.CTkFrame):
    def __init__(
        self,
        master,
        text: str = "Ready",
        *,
        state: str = "ready",
        command: Callable | None = None,
        **kwargs,
    ) -> None:
        fg, bg = status_badge(state)
        super().__init__(master, fg_color=bg, corner_radius=T.PILL_RADIUS, **kwargs)
        self._command = command
        if command is not None:
            self.configure(cursor="hand2")

        self._dot = ctk.CTkLabel(self, text="●", font=T.FONT_SMALL, text_color=fg)
        self._dot.pack(side="left", padx=(8, 2), pady=4)
        self._label = ctk.CTkLabel(self, text=text, font=T.FONT_SMALL, text_color=fg)
        self._label.pack(side="left", padx=(0, 10), pady=4)

        if command is not None:
            self.bind("<Button-1>", lambda _e: self._on_click())
            self._dot.bind("<Button-1>", lambda _e: self._on_click())
            self._label.bind("<Button-1>", lambda _e: self._on_click())

    def _on_click(self) -> None:
        if self._command is not None:
            self._command()

    def set_state(self, text: str, state: str | tuple[str, str]) -> None:
        if isinstance(state, tuple):
            fg, bg = state
        else:
            fg, bg = status_badge(state)
        self._label.configure(text=text)
        self._dot.configure(text_color=fg)
        self._label.configure(text_color=fg)
        self.configure(fg_color=bg)
