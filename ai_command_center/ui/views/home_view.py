"""Home dashboard — quick actions, live status strip, recent activity (Phase 3D)."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.theme import tokens as T

_QUICK_ACTIONS: tuple[tuple[str, str, str], ...] = (
    ("\u2318  Ask AI",         "Type any question in the command box below",                "accent"),
    ("\U0001f4cb  Clipboard",  "Type \u201csummarize clipboard\u201d to process copied text",     "secondary"),
    ("\U0001f4dd  Notes",      "Type \u201cnote: keyword\u201d to search your Obsidian vault",    "secondary"),
    ("\U0001f4be  Remember",   "Type \u201cremember: label | content\u201d to store a memory",    "secondary"),
    (">_  Shell",              "Type \u201c> command\u201d to run a shell command",               "secondary"),
    ("\U0001f9e0  Memory",     "Type \u201cmemory: keyword\u201d to recall stored facts",         "secondary"),
)


def _accent_for(key: str) -> str:
    return T.ACCENT_DEFAULT if key == "accent" else T.TEXT_SECONDARY


# ──────────────────────────────────────────────────────────────────────────────
#  Internal widgets
# ──────────────────────────────────────────────────────────────────────────────

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


class _StatusPill(ctk.CTkFrame):
    """Single live-status indicator: dot + label + sub-label."""

    _DOT_UNKNOWN = "\u25cb"   # ○
    _DOT_OK      = "\u25cf"   # ●
    _DOT_BUSY    = "\u25d4"   # ◔
    _DOT_ERROR   = "\u25cf"   # ●

    def __init__(self, master, title: str) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=8,
        )
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 2))

        self._dot = ctk.CTkLabel(
            top,
            text=self._DOT_UNKNOWN,
            font=(T.FONT_FAMILY, 13, "bold"),
            text_color=T.TEXT_MUTED,
            width=16,
        )
        self._dot.pack(side="left")

        ctk.CTkLabel(
            top,
            text=title.upper(),
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(4, 0))

        self._main_lbl = ctk.CTkLabel(
            self,
            text="\u2014",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._main_lbl.pack(fill="x", padx=12, pady=(0, 4))

        self._sub_lbl = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._sub_lbl.pack(fill="x", padx=12, pady=(0, 10))

    def set_ok(self, main: str, sub: str = "") -> None:
        self._dot.configure(text=self._DOT_OK, text_color=T.STATUS_READY)
        self._main_lbl.configure(text=main, text_color=T.STATUS_READY)
        self._sub_lbl.configure(text=sub, text_color=T.TEXT_MUTED)

    def set_busy(self, main: str, sub: str = "") -> None:
        self._dot.configure(text=self._DOT_BUSY, text_color=T.STATUS_BUSY)
        self._main_lbl.configure(text=main, text_color=T.STATUS_BUSY)
        self._sub_lbl.configure(text=sub, text_color=T.TEXT_MUTED)

    def set_error(self, main: str, sub: str = "") -> None:
        self._dot.configure(text=self._DOT_ERROR, text_color=T.STATUS_ERROR)
        self._main_lbl.configure(text=main, text_color=T.STATUS_ERROR)
        self._sub_lbl.configure(text=sub, text_color=T.TEXT_MUTED)

    def set_unknown(self, main: str = "\u2014", sub: str = "") -> None:
        self._dot.configure(text=self._DOT_UNKNOWN, text_color=T.TEXT_MUTED)
        self._main_lbl.configure(text=main, text_color=T.TEXT_MUTED)
        self._sub_lbl.configure(text=sub, text_color=T.TEXT_MUTED)


# ──────────────────────────────────────────────────────────────────────────────
#  HomeView
# ──────────────────────────────────────────────────────────────────────────────

class HomeView(ctk.CTkFrame):
    """Home dashboard shown on launch.

    Architecture contract:
      - Receives event-driven updates only via public methods called from
        app.py after UIQueue dispatch. No EventBus or service imports here.
      - update_ollama()    ← wired to ollama.status
      - update_vault()     ← wired to note.index_complete / note.index_progress
      - update_memory()    ← wired to memory.stored
      - set_last_command() ← called from _apply_state()
    """

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._memory_count = 0
        self._build()

    # ── layout ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Hero banner
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
            text=(
                "Your local AI assistant \u2014 "
                "ask questions, search notes, run shell commands, remember facts."
            ),
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            wraplength=900,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(0, 14))

        # Live status strip
        ctk.CTkLabel(
            self,
            text="LIVE STATUS",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD + 2, pady=(4, 4))

        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.pack(fill="x", padx=T.PAD, pady=(0, 10))
        status_row.columnconfigure((0, 1, 2), weight=1, uniform="scol")

        self._pill_ollama = _StatusPill(status_row, "Ollama")
        self._pill_ollama.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self._pill_vault = _StatusPill(status_row, "Vault")
        self._pill_vault.grid(row=0, column=1, sticky="nsew", padx=4)

        self._pill_memory = _StatusPill(status_row, "Memory")
        self._pill_memory.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        # Quick actions
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

        # Recent activity
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

    # ── public API — called from app.py via UIQueue ───────────────────────────

    def update_ollama(self, online: bool, model: str = "") -> None:
        """Reflect live ollama.status event."""
        if online:
            sub = f"model: {model}" if model else "connected"
            self._pill_ollama.set_ok("Online", sub)
        else:
            self._pill_ollama.set_error("Offline", "Ollama not reachable")

    def update_vault(self, *, indexing: bool = False, files: int = 0, ms: int = 0) -> None:
        """Reflect note.index_progress or note.index_complete events."""
        if indexing:
            self._pill_vault.set_busy("Indexing\u2026", f"{files} files so far")
        elif files > 0:
            duration = f"{ms} ms" if ms else ""
            self._pill_vault.set_ok(f"{files} notes indexed", duration)
        else:
            self._pill_vault.set_unknown("Not configured", "Set vault path in Settings")

    def update_memory(self, count: int) -> None:
        """Reflect memory.stored — increments displayed count."""
        self._memory_count = count
        if count == 0:
            self._pill_memory.set_unknown("No memories", "Use \u201cremember:\u201d to store facts")
        else:
            self._pill_memory.set_ok(f"{count} memor{'y' if count == 1 else 'ies'} stored")

    def set_last_command(self, text: str) -> None:
        self._last_cmd.configure(text=text, text_color=T.TEXT_SECONDARY)

    def set_extra(self, text: str) -> None:
        """Compatibility shim \u2014 same signature as PlaceholderView."""
        self.set_last_command(text)
