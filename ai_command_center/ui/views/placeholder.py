"""Placeholder views — Phase 3+ will flesh out."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.theme import tokens as T

VIEW_LABELS: dict[str, str] = {
    "home": "Home Dashboard",
    "chat": "Chat Workspace",
    "notes": "Obsidian Notes",
    "memory": "Memory",
    "system": "System Monitor",
    "plugins": "Plugins",
    "settings": "Settings",
}

VIEW_HINTS: dict[str, str] = {
    "home": "Quick actions and system overview.",
    "chat": "Ollama streaming chat.",
    "notes": "Vault search and quick notes.",
    "memory": "Browse and manage stored memories.",
    "system": "CPU, RAM, and shared memory monitor.",
    "plugins": "Plugin manager.",
    "settings": "Accent, hotkey, low memory mode.",
}


class PlaceholderView(ctk.CTkFrame):
    def __init__(self, master, view_id: str, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        card = GlassCard(self)
        card.pack(fill="both", expand=True, padx=T.PAD, pady=(T.PAD, 8))

        ctk.CTkLabel(
            card,
            text=VIEW_LABELS.get(view_id, view_id.title()),
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 8))

        self._hint = ctk.CTkLabel(
            card,
            text=VIEW_HINTS.get(view_id, ""),
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            wraplength=700,
            justify="left",
        )
        self._hint.pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))

        self._extra = ctk.CTkLabel(
            card,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            justify="left",
        )
        self._extra.pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))

    def set_extra(self, text: str) -> None:
        self._extra.configure(text=text)
