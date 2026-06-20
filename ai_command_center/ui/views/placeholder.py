"""Placeholder views — Phase 3+ will flesh out."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.floating_ui import pack_floating
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.layer.layer_stack import PageLayerStack
from ai_command_center.ui.theme import tokens as T

VIEW_LABELS: dict[str, str] = {
    "home": "Home Dashboard",
    "chat": "Chat Workspace",
    "notes": "Obsidian Notes",
    "system": "System Monitor",
    "plugins": "Plugins",
    "settings": "Settings",
}

VIEW_HINTS: dict[str, str] = {
    "home": "Quick actions and system overview — Phase 3.",
    "chat": "Ollama streaming chat — Phase 3.",
    "notes": "Vault search and quick notes — Phase 3.",
    "system": "CPU, RAM, shared memory — Phase 4.",
    "plugins": "Plugin manager — Phase 4.",
    "settings": "Accent, hotkey, low memory mode — coming soon.",
}


class PlaceholderView(PageLayerStack):
    def __init__(self, master, view_id: str, **kwargs) -> None:
        page = view_id if view_id in ("home", "system", "chat", "notes", "plugins", "settings") else "settings"
        super().__init__(master, page, **kwargs)
        card = GlassCard(self.ui_layer)
        pack_floating(card, fill="both", expand=True, first=True)

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
