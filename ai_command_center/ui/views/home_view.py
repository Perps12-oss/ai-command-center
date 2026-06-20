"""Home dashboard — quick actions + status overview (Phase 3D)."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.theme import tokens as T

_QUICK_ACTIONS: tuple[tuple[str, str, str], ...] = (
    ("\u2318  Ask AI",      "Type any question in the command box below",             "accent"),
    ("\U0001f4cb  Clipboard", "Type \u201csummarize clipboard\u201d to process copied text",    "secondary"),
    ("\U0001f4dd  Notes",     "Type \u201cnote: keyword\u201d to search your Obsidian vault",   "secondary"),
    ("\U0001f4be  Remember",  "Type \u201cremember: label | content\u201d to store a memory",   "secondary"),
    (">_  Shell",           "Type \u201c> command\u201d to run a shell command",                "secondary"),
    ("\U0001f9e0  Memory",    "Type \u201cmemory: keyword\u201d to recall stored facts",        "secondary"),
)


def _accent_for(key: str) -> str:
    return T.ACCENT_DEFAULT if key == "accent" else T.TEXT_SECONDARY


class _ActionCard(ctk.CTkFrame):
    def __init__(self, master, icon_title: str, hint: str, color_key: str) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=8,
        )
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


class HomeView(ctk.CTkFrame):
    """Home dashboard shown on launch.

    Architecture contract:
      - Receives updates via set_last_command() from app.py (_apply_state).
      - No EventBus or service imports.
    """

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._build()

    def _build(self) -> None:
        # ── Hero banner ───────────────────────────────────────────────────────
        hero = GlassCard(self)
        hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        hero_inner = ctk.CTkFrame(hero, fg_color="transparent")
        hero_inner.pack(fill="x", padx=T.PAD, pady=14)

        ctk.CTkLabel(
            hero_inner,
            text="\u25c7  AI Command Center",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            hero_inner,
            text="Alt+Space to toggle",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(side="right")

        ctk.CTkLabel(
            hero,
            text="Your local AI assistant \u2014 ask questions, search notes, run shell commands, remember facts.",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            wraplength=900,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(0, 14))

        # ── Quick actions grid ────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="QUICK ACTIONS",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD + 2, pady=(4, 4))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=T.PAD, pady=(0, 8))
        grid.columnconfigure((0, 1, 2), weight=1, uniform="col")

        for i, (title, hint, color_key) in enumerate(_QUICK_ACTIONS):
            card = _ActionCard(grid, title, hint, color_key)
            card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=4, pady=4)

        # ── Recent activity ───────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="RECENT ACTIVITY",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD + 2, pady=(8, 4))

        activity_card = GlassCard(self)
        activity_card.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        self._last_cmd = ctk.CTkLabel(
            activity_card,
            text="No commands yet \u2014 start typing above.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self._last_cmd.pack(fill="x", padx=T.PAD, pady=12)

    # ── public API ─────────────────────────────────────────────────────────────

    def set_last_command(self, text: str) -> None:
        self._last_cmd.configure(text=text, text_color=T.TEXT_SECONDARY)

    def set_extra(self, text: str) -> None:
        """Compatibility shim \u2014 same signature as PlaceholderView."""
        self.set_last_command(text)
