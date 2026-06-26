"""Home dashboard — live status, activity feed, quick stats, quick actions."""
from __future__ import annotations

import time
from collections import deque

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.theme import tokens as T

_QUICK_ACTIONS: tuple[tuple[str, str, str], ...] = (
    ("\u2318  Ask AI",        "Type any question in the command box below",                  "accent"),
    ("\U0001f4cb  Clipboard", "Type \u201csummarize clipboard\u201d to process copied text", "secondary"),
    ("\U0001f4dd  Notes",     "Type \u201cnote: keyword\u201d to search your Obsidian vault", "secondary"),
    ("\U0001f4be  Remember",  "Type \u201cremember: label | content\u201d to store a memory", "secondary"),
    (">_  Shell",             "Type \u201c> command\u201d to run a shell command",            "secondary"),
    ("\U0001f9e0  Memory",    "Type \u201cmemory: keyword\u201d to recall stored facts",      "secondary"),
)

_ACTIVITY_ICON = {
    "chat":    "💬",
    "note":    "📝",
    "memory":  "🧠",
    "tool":    "🔧",
    "system":  "⚙",
    "error":   "✕",
}

_MAX_ACTIVITY = 5


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

    _DOT_UNKNOWN = "\u25cb"
    _DOT_OK      = "\u25cf"
    _DOT_BUSY    = "\u25d4"
    _DOT_ERROR   = "\u25cf"

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
            self, text="\u2014", font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w"
        )
        self._main_lbl.pack(fill="x", padx=12, pady=(0, 4))

        self._sub_lbl = ctk.CTkLabel(
            self, text="", font=(T.FONT_FAMILY, 10), text_color=T.TEXT_MUTED, anchor="w"
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


class _StatsStrip(ctk.CTkFrame):
    """Row of quick-stat counters: messages · memories · notes."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color=T.BG_GLASS, corner_radius=8)
        self._labels: dict[str, ctk.CTkLabel] = {}
        for key, title in (("messages", "Messages"), ("memories", "Memories"), ("notes", "Notes")):
            col = ctk.CTkFrame(self, fg_color="transparent")
            col.pack(side="left", fill="both", expand=True, padx=16, pady=10)
            val = ctk.CTkLabel(col, text="0", font=T.FONT_HEADER, text_color=T.TEXT_PRIMARY, anchor="center")
            val.pack(fill="x")
            ctk.CTkLabel(col, text=title, font=(T.FONT_FAMILY, 10), text_color=T.TEXT_MUTED, anchor="center").pack(fill="x")
            self._labels[key] = val

    def update(self, messages: int, memories: int, notes: int) -> None:
        self._labels["messages"].configure(text=str(messages))
        self._labels["memories"].configure(text=str(memories))
        self._labels["notes"].configure(text=str(notes))


class _ActivityFeed(ctk.CTkFrame):
    """Shows the last N events as rows inside a GlassCard."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self._entries: deque[tuple[str, str, str]] = deque(maxlen=_MAX_ACTIVITY)
        self._row_frames: list[ctk.CTkFrame] = []
        self._build_rows()

    def _build_rows(self) -> None:
        for f in self._row_frames:
            f.destroy()
        self._row_frames.clear()

        if not self._entries:
            placeholder = ctk.CTkFrame(self, fg_color="transparent")
            placeholder.pack(fill="x", padx=T.PAD, pady=10)
            ctk.CTkLabel(
                placeholder,
                text="No activity yet \u2014 start typing above.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x")
            self._row_frames.append(placeholder)
            return

        for icon, text, ts in self._entries:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=T.PAD, pady=(4, 0))
            ctk.CTkLabel(row, text=icon, font=T.FONT_SMALL, text_color=T.ACCENT_DEFAULT, width=20).pack(side="left")
            ctk.CTkLabel(row, text=text, font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY, anchor="w", wraplength=560, justify="left").pack(side="left", fill="x", expand=True, padx=(6, 0))
            ctk.CTkLabel(row, text=ts, font=(T.FONT_FAMILY, 10), text_color=T.TEXT_MUTED).pack(side="right")
            self._row_frames.append(row)

    def add(self, text: str, kind: str = "system") -> None:
        icon = _ACTIVITY_ICON.get(kind, "◈")
        ts   = time.strftime("%H:%M")
        self._entries.appendleft((icon, text, ts))
        self._build_rows()


class _WorkspacePanel(ctk.CTkFrame):
    """Dedicated panel for the active workspace + its pre-AI suggestions."""

    _PLACEHOLDER = "No active workspace yet \u2014 run a command to resolve one."

    def __init__(self, master) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=8,
        )
        self._title = ctk.CTkLabel(
            self,
            text="\u2014",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title.pack(fill="x", padx=12, pady=(10, 0))

        self._meta = ctk.CTkLabel(
            self,
            text=self._PLACEHOLDER,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            wraplength=820,
            justify="left",
        )
        self._meta.pack(fill="x", padx=12, pady=(2, 6))

        self._suggestions = ctk.CTkFrame(self, fg_color="transparent")
        self._suggestions.pack(fill="x", padx=12, pady=(0, 10))
        self._suggestion_rows: list[ctk.CTkFrame] = []

    def _clear_suggestions(self) -> None:
        for row in self._suggestion_rows:
            row.destroy()
        self._suggestion_rows.clear()

    def update(
        self,
        *,
        title: str,
        inferred_task: str = "",
        confidence: float = 0.0,
        evidence_source: str = "",
        suggestions: tuple[tuple[str, str], ...] = (),
    ) -> None:
        title = title.strip()
        self._title.configure(text=title or "\u2014")

        meta_bits: list[str] = []
        if inferred_task.strip():
            meta_bits.append(inferred_task.strip())
        if evidence_source.strip():
            tail = f"via {evidence_source.strip()}"
            if confidence > 0:
                tail += f" ({confidence:.0%})"
            meta_bits.append(tail)
        self._meta.configure(
            text="  \u00b7  ".join(meta_bits) if meta_bits else self._PLACEHOLDER,
            text_color=T.TEXT_SECONDARY if meta_bits else T.TEXT_MUTED,
        )

        self._clear_suggestions()
        for label, command in suggestions[:4]:
            label = label.strip()
            if not label:
                continue
            row = ctk.CTkFrame(self._suggestions, fg_color="transparent")
            row.pack(fill="x", pady=(2, 0))
            ctk.CTkLabel(
                row,
                text=f"\u2192  {label}",
                font=T.FONT_SMALL,
                text_color=T.ACCENT_DEFAULT,
                anchor="w",
            ).pack(side="left")
            if command.strip():
                ctk.CTkLabel(
                    row,
                    text=command.strip(),
                    font=(T.FONT_FAMILY, 10),
                    text_color=T.TEXT_MUTED,
                    anchor="e",
                ).pack(side="right")
            self._suggestion_rows.append(row)


# ──────────────────────────────────────────────────────────────────────────────
#  HomeView
# ──────────────────────────────────────────────────────────────────────────────

class HomeView(ctk.CTkFrame):
    """Home dashboard.

    Architecture contract — public API called from app.py via UIQueue:
      update_ollama(online, model)
      update_vault(*, indexing, files, ms)
      update_vault_search(query, count)
      update_memory(count)
      update_stats(messages, memories, notes)
      update_workspace(*, title, inferred_task, confidence, evidence_source, suggestions)
      add_activity(text, kind)
      set_last_command(text)       (legacy compat)
    """

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._memory_count = 0
        self._build()

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        # Hero banner
        hero = GlassCard(scroll)
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
            text="Alt+Space to toggle  ·  Ctrl+K for commands  ·  ? for shortcuts",
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

        # Active workspace panel
        ctk.CTkLabel(
            scroll, text="ACTIVE WORKSPACE", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=T.PAD + 2, pady=(4, 4))
        self._workspace = _WorkspacePanel(scroll)
        self._workspace.pack(fill="x", padx=T.PAD, pady=(0, 8))

        # Quick stats strip
        ctk.CTkLabel(
            scroll, text="QUICK STATS", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=T.PAD + 2, pady=(4, 4))
        self._stats = _StatsStrip(scroll)
        self._stats.pack(fill="x", padx=T.PAD, pady=(0, 8))

        # Live status strip
        ctk.CTkLabel(
            scroll, text="LIVE STATUS", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=T.PAD + 2, pady=(4, 4))
        status_row = ctk.CTkFrame(scroll, fg_color="transparent")
        status_row.pack(fill="x", padx=T.PAD, pady=(0, 10))
        status_row.columnconfigure((0, 1, 2), weight=1, uniform="scol")
        self._pill_ollama = _StatusPill(status_row, "Ollama")
        self._pill_ollama.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self._pill_vault  = _StatusPill(status_row, "Vault")
        self._pill_vault.grid(row=0, column=1, sticky="nsew", padx=4)
        self._pill_memory = _StatusPill(status_row, "Memory")
        self._pill_memory.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        # Quick actions
        ctk.CTkLabel(
            scroll, text="QUICK ACTIONS", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=T.PAD + 2, pady=(4, 4))
        grid = ctk.CTkFrame(scroll, fg_color="transparent")
        grid.pack(fill="x", padx=T.PAD, pady=(0, 8))
        grid.columnconfigure((0, 1, 2), weight=1, uniform="col")
        for i, (title, hint, color_key) in enumerate(_QUICK_ACTIONS):
            _ActionCard(grid, title, hint, color_key).grid(
                row=i // 3, column=i % 3, sticky="nsew", padx=4, pady=4
            )

        # Recent activity feed
        ctk.CTkLabel(
            scroll, text="RECENT ACTIVITY", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=T.PAD + 2, pady=(8, 4))
        activity_card = GlassCard(scroll)
        activity_card.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        self._activity_feed = _ActivityFeed(activity_card)
        self._activity_feed.pack(fill="x", pady=(4, 8))

    # ── public API ─────────────────────────────────────────────────────────────

    def update_ollama(self, online: bool, model: str = "") -> None:
        if online:
            self._pill_ollama.set_ok("Online", f"model: {model}" if model else "connected")
        else:
            self._pill_ollama.set_error("Offline", "Ollama not reachable")

    def update_vault(self, *, indexing: bool = False, files: int = 0, ms: int = 0) -> None:
        if indexing:
            self._pill_vault.set_busy("Indexing\u2026", f"{files} files so far")
        elif files > 0:
            self._pill_vault.set_ok(f"{files} notes indexed", f"{ms} ms" if ms else "")
        else:
            self._pill_vault.set_unknown("Not configured", "Set vault path in Settings")

    def update_vault_search(self, query: str, count: int) -> None:
        short_q = (query[:28] + "\u2026") if len(query) > 28 else query
        if count > 0:
            self._pill_vault.set_ok(f"{count} result{'s' if count != 1 else ''}", f"note: {short_q}")
        else:
            self._pill_vault.set_busy("No results", f"note: {short_q}")

    def update_memory(self, count: int) -> None:
        self._memory_count = count
        if count == 0:
            self._pill_memory.set_unknown("No memories", "Use \u201cremember:\u201d to store facts")
        else:
            self._pill_memory.set_ok(f"{count} memor{'y' if count == 1 else 'ies'} stored")

    def update_stats(self, messages: int = 0, memories: int = 0, notes: int = 0) -> None:
        self._stats.update(messages, memories, notes)

    def update_workspace(
        self,
        *,
        title: str,
        inferred_task: str = "",
        confidence: float = 0.0,
        evidence_source: str = "",
        suggestions: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self._workspace.update(
            title=title,
            inferred_task=inferred_task,
            confidence=confidence,
            evidence_source=evidence_source,
            suggestions=suggestions,
        )

    def add_activity(self, text: str, kind: str = "system") -> None:
        self._activity_feed.add(text, kind)

    def set_last_command(self, text: str) -> None:
        self._activity_feed.add(text, "system")

    def set_extra(self, text: str) -> None:
        self.set_last_command(text)
