"""Conversation history sidebar — in-memory session list with auto-titles."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T

_PANEL_W   = 210
_ROW_H     = 58


class _SessionRow(ctk.CTkFrame):
    """Single session entry: title chip + timestamp + delete button."""

    def __init__(
        self,
        master,
        sid:       str,
        title:     str,
        ts:        str,
        active:    bool,
        on_select: Callable[[str], None],
        on_delete: Callable[[str], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=T.ACCENT_DEFAULT if active else "transparent",
            corner_radius=8,
            cursor="hand2",
        )
        self._sid       = sid
        self._active    = active
        self._on_select = on_select
        self._on_delete = on_delete

        # Click anywhere on the row to select
        self.bind("<Button-1>", self._select)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=6)
        inner.bind("<Button-1>", self._select)

        # Title
        self._title_lbl = ctk.CTkLabel(
            inner,
            text=title,
            font=(T.FONT_FAMILY, 12, "bold") if active else T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY if active else T.TEXT_SECONDARY,
            anchor="w",
            wraplength=_PANEL_W - 52,
            justify="left",
        )
        self._title_lbl.pack(fill="x", anchor="w")
        self._title_lbl.bind("<Button-1>", self._select)

        # Timestamp row
        ts_row = ctk.CTkFrame(inner, fg_color="transparent")
        ts_row.pack(fill="x", pady=(2, 0))
        ts_row.bind("<Button-1>", self._select)

        ctk.CTkLabel(
            ts_row,
            text=ts,
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_PRIMARY if active else T.TEXT_MUTED,
            anchor="w",
        ).pack(side="left")

        # Delete button (only visible on hover via always-present muted icon)
        self._del_btn = ctk.CTkButton(
            ts_row,
            text="×",
            width=18, height=18,
            font=(T.FONT_FAMILY, 12),
            fg_color="transparent",
            hover_color=T.STATUS_ERROR,
            text_color=T.BG_GLASS_BORDER,
            corner_radius=4,
            command=self._delete,
        )
        self._del_btn.pack(side="right")

    def _select(self, _event=None) -> None:
        self._on_select(self._sid)

    def _delete(self) -> None:
        self._on_delete(self._sid)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(fg_color=T.ACCENT_DEFAULT if active else "transparent")
        self._title_lbl.configure(
            font=(T.FONT_FAMILY, 12, "bold") if active else T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY if active else T.TEXT_SECONDARY,
        )


class ChatHistoryPanel(ctk.CTkFrame):
    """Collapsible left sidebar listing in-memory chat sessions.

    Public API (called from ChatView)
    ──────────────────────────────────
    add_session(sid, title, ts, active)
    set_active(sid)
    remove_session(sid)
    clear()
    """

    def __init__(
        self,
        master,
        on_new:    Callable[[], None],
        on_select: Callable[[str], None],
        on_delete: Callable[[str], None],
    ) -> None:
        super().__init__(
            master,
            width=_PANEL_W,
            fg_color=T.BG_PANEL,
            corner_radius=0,
        )
        self.pack_propagate(False)
        self._on_new    = on_new
        self._on_select = on_select
        self._on_delete = on_delete
        self._rows: dict[str, _SessionRow] = {}

        # ── Header ─────────────────────────────────────────────────────────────
        ctk.CTkButton(
            self,
            text="＋  New Chat",
            height=34,
            font=(T.FONT_FAMILY, 12, "bold"),
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=8,
            command=on_new,
        ).pack(fill="x", padx=10, pady=(12, 6))

        ctk.CTkFrame(self, height=1, fg_color=T.BG_GLASS_BORDER).pack(
            fill="x", padx=10, pady=(0, 4)
        )

        ctk.CTkLabel(
            self,
            text="RECENT",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 2))

        # ── Scrollable list ─────────────────────────────────────────────────────
        self._list = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self._list.pack(fill="both", expand=True, padx=4)

        # Empty placeholder
        self._placeholder = ctk.CTkLabel(
            self._list,
            text="No sessions yet.\nStart typing to\ncreate one.",
            font=(T.FONT_FAMILY, 11),
            text_color=T.TEXT_MUTED,
            justify="center",
        )
        self._placeholder.pack(pady=28)

    # ── public API ─────────────────────────────────────────────────────────────

    def add_session(
        self, sid: str, title: str, ts: str, *, active: bool = False
    ) -> None:
        if self._placeholder.winfo_ismapped():
            self._placeholder.pack_forget()

        # Remove old row if it exists (re-add at top)
        if sid in self._rows:
            self._rows[sid].pack_forget()
            del self._rows[sid]

        row = _SessionRow(
            self._list,
            sid=sid, title=title, ts=ts, active=active,
            on_select=self._on_select,
            on_delete=self._on_delete,
        )
        row.pack(fill="x", pady=(0, 2))
        # Move to top: repack all rows
        row.pack_forget()
        for existing in self._rows.values():
            existing.pack_forget()
        row.pack(fill="x", pady=(0, 2))
        self._rows[sid] = row
        for existing_sid, existing_row in self._rows.items():
            if existing_sid != sid:
                existing_row.pack(fill="x", pady=(0, 2))

    def set_active(self, sid: str) -> None:
        for row_sid, row in self._rows.items():
            row.set_active(row_sid == sid)

    def remove_session(self, sid: str) -> None:
        row = self._rows.pop(sid, None)
        if row:
            row.destroy()
        if not self._rows:
            self._placeholder.pack(pady=28)

    def clear(self) -> None:
        for row in self._rows.values():
            row.destroy()
        self._rows.clear()
        self._placeholder.pack(pady=28)
