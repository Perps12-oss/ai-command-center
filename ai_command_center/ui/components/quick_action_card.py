"""Quick action cards shared by Command Center (extracted from HomeView)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

QUICK_ACTIONS: tuple[tuple[str, str, str, str], ...] = (
    ("⌘  Ask AI", "Type any question in the command box below", "accent", "What can you help me with?"),
    ("📋  Clipboard", "Type “summarize clipboard” to process copied text", "secondary", "summarize clipboard"),
    ("📝  Notes", "Type “note: keyword” to search your Obsidian vault", "secondary", "note: "),
    ("💾  Remember", "Type “remember: label | content” to store a memory", "secondary", "remember: | "),
    (">_  Shell", "Type “> command” to run a shell command", "secondary", "> "),
    ("🧠  Memory", "Type “memory: keyword” to recall stored facts", "secondary", "memory: "),
)


def _accent_for(key: str) -> str:
    return T.ACCENT_DEFAULT if key == "accent" else T.TEXT_SECONDARY


class ActionCard(ctk.CTkFrame):
    """Clickable quick-action tile that invokes a command callback."""

    def __init__(
        self,
        master: Any,
        icon_title: str,
        hint: str,
        color_key: str,
        command: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
        )
        self._command = command
        self._default_border = T.BG_GLASS_BORDER
        self._hover_border = T.GLASS_BORDER_HOVER
        ctk.CTkLabel(
            self,
            text=icon_title,
            font=T.FONT_HEADER,
            text_color=_accent_for(color_key),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            self,
            text=hint,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            wraplength=260,
            justify="left",
        ).pack(fill="x", padx=12, pady=(0, 10))
        if command is not None:
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self.bind("<Button-1>", lambda _e: self._on_click())
            for child in self.winfo_children():
                child.bind("<Button-1>", lambda _e: self._on_click())

    def _on_enter(self, _event: object) -> None:
        self.configure(border_color=self._hover_border)

    def _on_leave(self, _event: object) -> None:
        self.configure(border_color=self._default_border)

    def _on_click(self) -> None:
        if self._command is not None:
            self._command()


# Backward-compatible aliases used by HomeView
_ActionCard = ActionCard
_QUICK_ACTIONS = QUICK_ACTIONS

__all__ = ["ActionCard", "QUICK_ACTIONS", "_ActionCard", "_QUICK_ACTIONS"]
