"""Placeholder views — Phase 3+ will flesh out."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T

VIEW_LABELS: dict[str, str] = {
    "home": "Home Dashboard",
    "command_center": "Command Center",
    "chat": "Chat Workspace",
    "notes": "Obsidian Notes",
    "memory": "Memory",
    "system": "System Monitor",
    "plugins": "Plugins",
    "settings": "Settings",
    "goals": "Goal Dashboard",
    "agents": "Agent Monitor",
    "approvals": "Approval Center",
}

VIEW_HINTS: dict[str, str] = {
    "home": "Quick actions and system overview.",
    "command_center": "Operational overview and mission control.",
    "chat": "Ollama streaming chat.",
    "notes": "Vault search and quick notes.",
    "memory": "Browse and manage stored memories.",
    "system": "CPU, RAM, and shared memory monitor.",
    "plugins": "Plugin manager.",
    "settings": "Accent, hotkey, low memory mode.",
    "goals": "Goal lifecycle dashboard — under construction (Phase 11F).",
    "agents": "Active agent runs and pipeline monitor — under construction (Phase 11D).",
    "approvals": "Pending permission checks and decision history — under construction (Phase 11E).",
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
