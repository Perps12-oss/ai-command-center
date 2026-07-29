"""Home dashboard — superseded by CommandCenterView; retained for widget reuse."""
from __future__ import annotations

import datetime
import time
from collections import deque

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.components.quick_action_card import (
    ActionCard as _ActionCard,
    QUICK_ACTIONS as _QUICK_ACTIONS,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children

_ACTIVITY_ICON = {
    "chat":    "💬",
    "note":    "📝",
    "memory":  "🧠",
    "tool":    "🔧",
    "system":  "⚙",
    "error":   "✕",
}

_MAX_ACTIVITY = 5


# ──────────────────────────────────────────────────────────────────────────────
#  Internal widgets
# ──────────────────────────────────────────────────────────────────────────────

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
            corner_radius=T.CARD_RADIUS,
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
        super().__init__(master, fg_color=T.BG_GLASS, corner_radius=T.CARD_RADIUS)
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
            empty_row = ctk.CTkFrame(self, fg_color="transparent")
            empty_row.pack(fill="x", padx=T.PAD, pady=10)
            ctk.CTkLabel(
                empty_row,
                text="No activity yet \u2014 start typing above.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x")
            self._row_frames.append(empty_row)
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
      add_activity(text, kind)
      set_last_command(text)       (legacy compat)
    """

    @staticmethod
    def _greeting() -> str:
        hour = datetime.datetime.now().hour
        if hour < 12:
            return "Good morning ◇"
        if hour < 17:
            return "Good afternoon ◇"
        return "Good evening ◇"

    def __init__(self, master, *, on_command=None, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_command = on_command
        self._memory_count = 0
        self._note_count = 0
        self._msg_count = 0
        self._build()

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        # Hero banner
        hero = GlassCard(scroll)
        hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))
        hero_inner = ctk.CTkFrame(hero, fg_color="transparent")
        hero_inner.pack(fill="x", padx=T.PAD, pady=(14, 4))
        self._greeting_lbl = ctk.CTkLabel(
            hero_inner,
            text=self._greeting(),
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        )
        self._greeting_lbl.pack(side="left")
        ctk.CTkLabel(
            hero_inner,
            text="Alt+Space to toggle  ·  Ctrl+K for commands  ·  ? for shortcuts",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(side="right")
        self._summary_lbl = ctk.CTkLabel(
            hero,
            text="Loading…",
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._summary_lbl.pack(fill="x", padx=T.PAD, pady=(0, 14))

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
        for i, (title, hint, color_key, command_text) in enumerate(_QUICK_ACTIONS):
            cmd = (lambda t=command_text: self._publish_command(t)) if self._on_command else None
            _ActionCard(grid, title, hint, color_key, command=cmd).grid(
                row=i // 3, column=i % 3, sticky="nsew", padx=4, pady=4
            )

        # Pinned commands
        pin_hdr_row = ctk.CTkFrame(scroll, fg_color="transparent")
        pin_hdr_row.pack(fill="x", padx=T.PAD + 2, pady=(8, 4))
        ctk.CTkLabel(
            pin_hdr_row, text="PINNED COMMANDS", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(side="left")
        ctk.CTkButton(
            pin_hdr_row,
            text="+ Pin",
            width=52, height=20,
            font=(T.FONT_FAMILY, 10),
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
            command=self._show_pin_dialog,
        ).pack(side="right")
        self._pins_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._pins_frame.pack(fill="x", padx=T.PAD, pady=(0, 8))
        self._pinned_commands: list[str] = []
        self._render_pins()

        # Recent activity feed
        ctk.CTkLabel(
            scroll, text="RECENT ACTIVITY", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=T.PAD + 2, pady=(8, 4))
        activity_card = GlassCard(scroll)
        activity_card.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        self._activity_feed = _ActivityFeed(activity_card)
        self._activity_feed.pack(fill="x", pady=(4, 8))

    # ── pin management ─────────────────────────────────────────────────────────

    def _render_pins(self) -> None:
        clear_children(self._pins_frame)
        if not self._pinned_commands:
            ctk.CTkLabel(
                self._pins_frame,
                text="No pins yet — click + Pin to add a command shortcut.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", pady=2)
            return
        for cmd in self._pinned_commands:
            chip = ctk.CTkFrame(
                self._pins_frame,
                fg_color=T.BG_GLASS,
                border_color=T.BG_GLASS_BORDER,
                border_width=1,
                corner_radius=T.SMALL_RADIUS,
            )
            chip.pack(side="left", padx=(0, 6), pady=2)
            label = (cmd[:28] + "…") if len(cmd) > 28 else cmd
            ctk.CTkLabel(
                chip, text=label, font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY, anchor="w"
            ).pack(side="left", padx=(8, 2), pady=4)
            ctk.CTkButton(
                chip, text="✕",
                width=16, height=16,
                font=(T.FONT_FAMILY, 9),
                fg_color="transparent",
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=lambda c=cmd: self.remove_pin(c),
            ).pack(side="right", padx=(0, 4))
            chip.bind("<Button-1>", lambda _e, c=cmd: self._publish_command(c))
            for child in chip.winfo_children():
                if hasattr(child, "cget") and child.cget("text") not in ("✕",):
                    child.bind("<Button-1>", lambda _e, c=cmd: self._publish_command(c))

    def _show_pin_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Pin a command")
        dialog.configure(fg_color=T.BG_PANEL)
        dialog.geometry("400x160")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Command text to pin",
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 2))
        entry = ctk.CTkEntry(
            dialog, font=T.FONT_BODY,
            fg_color=T.BG_INPUT, border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY, placeholder_text="e.g. note: weekly review",
        )
        entry.pack(fill="x", padx=T.PAD)
        entry.focus_set()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(padx=T.PAD, pady=(12, 0))

        def _ok() -> None:
            text = entry.get().strip()
            if text:
                self.add_pin(text)
            dialog.destroy()

        ctk.CTkButton(
            btn_row, text="Cancel", font=T.FONT_SMALL,
            fg_color=T.BG_GLASS, hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY, command=dialog.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row, text="Pin", font=T.FONT_SMALL,
            fg_color=T.ACCENT_DEFAULT, hover_color=T.ACCENT_HOVER,
            text_color="white", command=_ok,
        ).pack(side="left")
        entry.bind("<Return>", lambda _e: _ok())

    def add_pin(self, command: str) -> None:
        if command not in self._pinned_commands:
            self._pinned_commands.append(command)
            self._render_pins()

    def remove_pin(self, command: str) -> None:
        if command in self._pinned_commands:
            self._pinned_commands.remove(command)
            self._render_pins()

    # ── public API ─────────────────────────────────────────────────────────────

    def _publish_command(self, text: str) -> None:
        if self._on_command is not None:
            self._on_command(text)

    def update_ollama(self, online: bool, model: str = "") -> None:
        if online:
            self._pill_ollama.set_ok("Online", f"model: {model}" if model else "connected")
        else:
            self._pill_ollama.set_error("Offline", "Ollama not reachable")

    def update_vault(self, *, indexing: bool = False, files: int = 0, ms: int = 0) -> None:
        self._note_count = files
        if indexing:
            self._pill_vault.set_busy("Indexing\u2026", f"{files} files so far")
        elif files > 0:
            self._pill_vault.set_ok(f"{files} notes indexed", f"{ms} ms" if ms else "")
            self._refresh_summary()
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
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        parts: list[str] = []
        if self._msg_count:
            parts.append(f"{self._msg_count} message{'s' if self._msg_count != 1 else ''}")
        if self._memory_count:
            parts.append(f"{self._memory_count} memor{'ies' if self._memory_count != 1 else 'y'}")
        if self._note_count:
            parts.append(f"{self._note_count} note{'s' if self._note_count != 1 else ''} indexed")
        text = " · ".join(parts) if parts else "No activity yet — start typing above."
        self._summary_lbl.configure(text=text, text_color=T.TEXT_SECONDARY if parts else T.TEXT_MUTED)

    def update_stats(self, messages: int = 0, memories: int = 0, notes: int = 0) -> None:
        self._msg_count = messages
        self._stats.update(messages, memories, notes)
        self._refresh_summary()

    def add_activity(self, text: str, kind: str = "system") -> None:
        self._activity_feed.add(text, kind)

    def apply_command_history(self, payload: dict) -> None:
        commands = payload.get("commands") or []
        total = int(payload.get("total", len(commands)))
        self._stats.update(
            messages=total,
            memories=self._memory_count,
            notes=self._note_count,
        )
        for item in commands[-3:]:
            detail = str(item.get("detail", item.get("text", "")))
            if detail:
                self.add_activity(detail, "system")

    def set_last_command(self, text: str) -> None:
        self._activity_feed.add(text, "system")

    def set_extra(self, text: str) -> None:
        self.set_last_command(text)

    # ── Program 4 dashboard summary cards ─────────────────────────────────────

    def update_execution_summary(
        self,
        active_count: int = 0,
        provider_health: str = "",
        artifact_count: int = 0,
        pending_approvals: int = 0,
    ) -> None:
        """Update the execution/provider/artifact/approval summary badges.

        Called from StateApplierMixin when AppState changes. The badges are
        rendered as activity feed items or pill sub-labels as appropriate.
        """
        if active_count > 0:
            self.add_activity(
                f"⚡  {active_count} active execution{'s' if active_count != 1 else ''}",
                "system",
            )
        if provider_health:
            self._pill_ollama.set_ok(provider_health, "provider health")
        if pending_approvals > 0:
            self.add_activity(
                f"⚠  {pending_approvals} pending approval{'s' if pending_approvals != 1 else ''}",
                "system",
            )
