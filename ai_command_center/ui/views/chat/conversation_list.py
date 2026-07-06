"""ConversationList — Open WebUI–style conversation rail.

IA sections (top to bottom):
  [+ New Chat] button
  [Search] entry
  Pinned group
  Recent group
  Folders (expandable)

Reference: Open WebUI sidebar conversation list IA.

Architecture contract
─────────────────────
• Pure display widget — no EventBus, no service imports.
• Receives ConversationMetadata items and calls back on selection / deletion.
• Extends SessionStore metadata without replacing it.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.conversation_metadata import ConversationMetadata

_SECTION_FONT = (T.FONT_FAMILY, 9)
_ITEM_FONT = (T.FONT_FAMILY, 11)
_TIME_FONT = (T.FONT_FAMILY, 9)
_BADGE_FONT = (T.FONT_FAMILY, 9)


class _ConversationRow(ctk.CTkFrame):
    """A single conversation item row."""

    def __init__(
        self,
        master: Any,
        meta: ConversationMetadata,
        on_select: Callable[[str], None],
        on_delete: Callable[[str], None],
        active: bool = False,
    ) -> None:
        bg = T.BG_GLASS if active else "transparent"
        super().__init__(
            master,
            fg_color=bg,
            corner_radius=T.SMALL_RADIUS,
            height=48,
        )
        self.pack_propagate(False)
        self._sid = meta.session_id
        self._active = active

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=6, pady=4)

        # title row
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")

        self._title_lbl = ctk.CTkLabel(
            title_row,
            text=meta.short_title(),
            font=_ITEM_FONT,
            text_color=T.TEXT_PRIMARY if active else T.TEXT_SECONDARY,
            anchor="w",
        )
        self._title_lbl.pack(side="left", fill="x", expand=True)

        if meta.pinned:
            ctk.CTkLabel(
                title_row,
                text="📌",
                font=_BADGE_FONT,
                text_color=T.ACCENT_DEFAULT,
            ).pack(side="right", padx=(2, 0))

        if meta.unread:
            ctk.CTkLabel(
                title_row,
                text=str(min(meta.unread, 99)),
                font=_BADGE_FONT,
                fg_color=T.ACCENT_DEFAULT,
                text_color="#FFFFFF",
                width=18, height=14,
                corner_radius=7,
            ).pack(side="right", padx=(2, 0))

        # sub-row: provider badge + time
        sub_row = ctk.CTkFrame(inner, fg_color="transparent")
        sub_row.pack(fill="x")

        if meta.provider_badge:
            ctk.CTkLabel(
                sub_row,
                text=meta.provider_badge,
                font=_TIME_FONT,
                text_color=T.TEXT_MUTED,
            ).pack(side="left")

        ctk.CTkLabel(
            sub_row,
            text=meta.display_time(),
            font=_TIME_FONT,
            text_color=T.TEXT_MUTED,
        ).pack(side="right")

        # click to select
        self.bind("<Button-1>", lambda _: on_select(self._sid))
        for child in self.winfo_children():
            _bind_recursive(child, "<Button-1>", lambda _, s=self._sid: on_select(s))

        self.bind("<Enter>", self._on_hover_enter)
        self.bind("<Leave>", self._on_hover_leave)

    def _on_hover_enter(self, _: Any = None) -> None:
        if not self._active:
            self.configure(fg_color=T.BG_GLASS)

    def _on_hover_leave(self, _: Any = None) -> None:
        if not self._active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(fg_color=T.BG_GLASS if active else "transparent")
        self._title_lbl.configure(
            text_color=T.TEXT_PRIMARY if active else T.TEXT_SECONDARY
        )


def _bind_recursive(widget: Any, event: str, callback: Callable) -> None:
    try:
        widget.bind(event, callback, add="+")
    except Exception:
        pass
    for child in widget.winfo_children():
        _bind_recursive(child, event, callback)


class _SectionHeader(ctk.CTkFrame):
    """Collapsible section header (Pinned / Recent / Folders)."""

    def __init__(
        self,
        master: Any,
        label: str,
        *,
        collapsible: bool = False,
        on_toggle: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent", height=24)
        self.pack_propagate(False)
        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=_SECTION_FONT,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(side="left", padx=8)
        if collapsible and on_toggle:
            ctk.CTkButton(
                self,
                text="▾",
                width=18, height=18,
                font=_SECTION_FONT,
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=on_toggle,
            ).pack(side="right", padx=4)


class ConversationList(ctk.CTkFrame):
    """Open WebUI–style conversation rail for the chat left pane.

    Parameters
    ──────────
    on_new      — called when the user clicks + New Chat
    on_select   — called with session_id when an item is clicked
    on_delete   — called with session_id when an item is deleted
    on_search   — called with query string when the search bar changes
    """

    def __init__(
        self,
        master: Any,
        on_new:    Callable[[], None],
        on_select: Callable[[str], None],
        on_delete: Callable[[str], None],
        on_search: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            corner_radius=0,
            **kwargs,
        )
        self._on_new = on_new
        self._on_select = on_select
        self._on_delete = on_delete
        self._on_search = on_search
        self._active_sid: str = ""
        self._rows: dict[str, _ConversationRow] = {}
        self._items: dict[str, ConversationMetadata] = {}

        self._build()

    def _build(self) -> None:
        # + New Chat
        ctk.CTkButton(
            self,
            text="+ New Chat",
            height=32,
            font=(T.FONT_FAMILY, 12),
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=T.SMALL_RADIUS,
            command=self._on_new,
        ).pack(fill="x", padx=10, pady=(10, 6))

        # Search bar
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        ctk.CTkEntry(
            self,
            placeholder_text="Search conversations…",
            textvariable=self._search_var,
            height=28,
            font=(T.FONT_FAMILY, 11),
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        ).pack(fill="x", padx=10, pady=(0, 6))

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self._scroll.pack(fill="both", expand=True, padx=4)
        self._scroll.columnconfigure(0, weight=1)

        self._pinned_header = _SectionHeader(self._scroll, "Pinned")
        self._pinned_section = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._recent_header = _SectionHeader(self._scroll, "Recent")
        self._recent_section = ctk.CTkFrame(self._scroll, fg_color="transparent")

        self._pinned_header.pack(fill="x", pady=(4, 0))
        self._pinned_section.pack(fill="x")
        self._recent_header.pack(fill="x", pady=(8, 0))
        self._recent_section.pack(fill="x")

    # ── public API ──────────────────────────────────────────────────────

    def add_conversation(self, meta: ConversationMetadata) -> None:
        """Prepend a conversation item to the appropriate section."""
        self._items[meta.session_id] = meta
        self._rebuild_list()

    def update_conversation(self, meta: ConversationMetadata) -> None:
        """Update an existing conversation item."""
        self._items[meta.session_id] = meta
        self._rebuild_list()

    def remove_conversation(self, session_id: str) -> None:
        """Remove a conversation item by session_id."""
        self._items.pop(session_id, None)
        self._rebuild_list()

    def set_active(self, session_id: str) -> None:
        """Highlight the active conversation row."""
        old = self._active_sid
        self._active_sid = session_id
        if old in self._rows:
            self._rows[old].set_active(False)
        if session_id in self._rows:
            self._rows[session_id].set_active(True)

    def load_sessions(
        self, sessions: list[tuple[str, str, str]]
    ) -> None:
        """Load sessions from legacy ChatHistoryPanel format.

        ``sessions`` is a list of (sid, title, timestamp_str) tuples.
        """
        for sid, title, ts_str in sessions:
            if sid not in self._items:
                meta = ConversationMetadata(
                    session_id=sid,
                    title=title,
                )
                self._items[sid] = meta
        self._rebuild_list()

    # ── private ─────────────────────────────────────────────────────────

    def _on_search_change(self, *_: Any) -> None:
        query = self._search_var.get()
        if self._on_search:
            self._on_search(query)
        self._rebuild_list(query=query)

    def _rebuild_list(self, *, query: str = "") -> None:
        """Destroy and recreate all row widgets from current _items state."""
        for row in self._rows.values():
            row.destroy()
        self._rows.clear()

        q = query.lower().strip()
        all_items = list(self._items.values())
        if q:
            all_items = [m for m in all_items if q in m.title.lower()]

        # Sort: pinned first by last_activity, then recent by last_activity
        pinned = sorted(
            [m for m in all_items if m.pinned and not m.archived],
            key=lambda m: m.last_activity,
            reverse=True,
        )
        recent = sorted(
            [m for m in all_items if not m.pinned and not m.archived],
            key=lambda m: m.last_activity,
            reverse=True,
        )

        show_pinned = bool(pinned)
        if show_pinned:
            self._pinned_header.pack(fill="x", pady=(4, 0))
            self._pinned_section.pack(fill="x")
        else:
            self._pinned_header.pack_forget()
            self._pinned_section.pack_forget()

        for meta in pinned:
            row = _ConversationRow(
                self._pinned_section,
                meta,
                on_select=self._on_select,
                on_delete=self._on_delete,
                active=meta.session_id == self._active_sid,
            )
            row.pack(fill="x", pady=1)
            self._rows[meta.session_id] = row

        for meta in recent:
            row = _ConversationRow(
                self._recent_section,
                meta,
                on_select=self._on_select,
                on_delete=self._on_delete,
                active=meta.session_id == self._active_sid,
            )
            row.pack(fill="x", pady=1)
            self._rows[meta.session_id] = row
