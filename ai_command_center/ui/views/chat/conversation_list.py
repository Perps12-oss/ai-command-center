"""ConversationList — Cursor-style conversation rail with date groups."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.conversation_metadata import ConversationMetadata

_SECTION_FONT = (T.FONT_FAMILY, 9)
_ITEM_FONT = (T.FONT_FAMILY, 11)
_TIME_FONT = (T.FONT_FAMILY, 9)
_PREVIEW_FONT = (T.FONT_FAMILY, 10)

_DATE_BUCKETS = ("Today", "Yesterday", "Previous 7 Days", "Older")


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
        bg = T.SURFACE_ELEVATED if active else "transparent"
        border = T.ACCENT_PURPLE if active else "transparent"
        super().__init__(
            master,
            fg_color=bg,
            corner_radius=T.BUTTON_RADIUS,
            height=64,
            border_width=1 if active else 0,
            border_color=border,
        )
        self.pack_propagate(False)
        self._sid = meta.session_id
        self._active = active
        self._hover_job: str | None = None

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=8, pady=6)

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

        ctk.CTkLabel(
            title_row,
            text=meta.display_time(),
            font=_TIME_FONT,
            text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=(4, 0))

        ctk.CTkLabel(
            inner,
            text=meta.preview_text(),
            font=_PREVIEW_FONT,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        self.bind("<Button-1>", lambda _: on_select(self._sid))
        for child in self.winfo_children():
            _bind_recursive(child, "<Button-1>", lambda _, s=self._sid: on_select(s))

        self.bind("<Enter>", self._on_hover_enter)
        self.bind("<Leave>", self._on_hover_leave)

    def _on_hover_enter(self, _: Any = None) -> None:
        if self._active:
            return
        if self._hover_job:
            self.after_cancel(self._hover_job)
        self._hover_job = self.after(T.HOVER_MS, lambda: self.configure(fg_color=T.SURFACE_ELEVATED))

    def _on_hover_leave(self, _: Any = None) -> None:
        if self._hover_job:
            self.after_cancel(self._hover_job)
            self._hover_job = None
        if not self._active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(
            fg_color=T.SURFACE_ELEVATED if active else "transparent",
            border_width=1 if active else 0,
            border_color=T.ACCENT_PURPLE if active else "transparent",
        )
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
    def __init__(self, master: Any, label: str) -> None:
        super().__init__(master, fg_color="transparent", height=24)
        self.pack_propagate(False)
        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=_SECTION_FONT,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(side="left", padx=8)


class ConversationList(ctk.CTkFrame):
    """Conversation rail for the chat left pane."""

    def __init__(
        self,
        master: Any,
        on_new: Callable[[], None],
        on_select: Callable[[str], None],
        on_delete: Callable[[str], None],
        on_search: Callable[[str], None] | None = None,
        on_view_all: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.SURFACE_PRIMARY,
            corner_radius=0,
            **kwargs,
        )
        self._on_new = on_new
        self._on_select = on_select
        self._on_delete = on_delete
        self._on_search = on_search
        self._on_view_all = on_view_all
        self._active_sid: str = ""
        self._rows: dict[str, _ConversationRow] = {}
        self._items: dict[str, ConversationMetadata] = {}
        self._section_frames: dict[str, ctk.CTkFrame] = {}
        self._section_headers: dict[str, _SectionHeader] = {}

        self._build()

    def _build(self) -> None:
        ctk.CTkButton(
            self,
            text="+ New Chat",
            height=36,
            font=(T.FONT_FAMILY, 12, "bold"),
            fg_color=T.ACCENT_PURPLE,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=T.INPUT_RADIUS,
            command=self._on_new,
        ).pack(fill="x", padx=10, pady=(10, 6))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        ctk.CTkEntry(
            self,
            placeholder_text="Search chats…",
            textvariable=self._search_var,
            height=32,
            font=(T.FONT_FAMILY, 11),
            fg_color=T.BG_INPUT,
            border_color=T.BORDER_SUBTLE,
            text_color=T.TEXT_PRIMARY,
            corner_radius=T.INPUT_RADIUS,
        ).pack(fill="x", padx=10, pady=(0, 6))

        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self._scroll.pack(fill="both", expand=True, padx=4)
        self._scroll.columnconfigure(0, weight=1)

        for bucket in _DATE_BUCKETS:
            header = _SectionHeader(self._scroll, bucket)
            section = ctk.CTkFrame(self._scroll, fg_color="transparent")
            self._section_headers[bucket] = header
            self._section_frames[bucket] = section

        ctk.CTkButton(
            self,
            text="View all chats →",
            height=28,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.SURFACE_ELEVATED,
            text_color=T.TEXT_MUTED,
            corner_radius=T.BUTTON_RADIUS,
            command=self._on_view_all_click,
        ).pack(fill="x", padx=10, pady=(4, 8))

    def _on_view_all_click(self) -> None:
        if self._on_view_all:
            self._on_view_all()

    def add_conversation(self, meta: ConversationMetadata) -> None:
        self._items[meta.session_id] = meta
        self._rebuild_list()

    def update_conversation(self, meta: ConversationMetadata) -> None:
        self._items[meta.session_id] = meta
        self._rebuild_list()

    def remove_conversation(self, session_id: str) -> None:
        self._items.pop(session_id, None)
        self._rebuild_list()

    def set_active(self, session_id: str) -> None:
        old = self._active_sid
        self._active_sid = session_id
        if old in self._rows:
            self._rows[old].set_active(False)
        if session_id in self._rows:
            self._rows[session_id].set_active(True)

    def load_sessions(self, sessions: list[tuple[str, str, str]]) -> None:
        for sid, title, _ts_str in sessions:
            if sid not in self._items:
                self._items[sid] = ConversationMetadata(session_id=sid, title=title)
        self._rebuild_list()

    def _on_search_change(self, *_: Any) -> None:
        query = self._search_var.get()
        if self._on_search:
            self._on_search(query)
        self._rebuild_list(query=query)

    def _rebuild_list(self, *, query: str = "") -> None:
        for row in self._rows.values():
            row.destroy()
        self._rows.clear()
        for section in self._section_frames.values():
            for child in section.winfo_children():
                child.destroy()
        for header in self._section_headers.values():
            header.pack_forget()
        for section in self._section_frames.values():
            section.pack_forget()

        q = query.lower().strip()
        all_items = list(self._items.values())
        if q:
            all_items = [
                m for m in all_items
                if q in m.title.lower() or q in m.preview.lower()
            ]
        all_items = [m for m in all_items if not m.archived]
        all_items.sort(key=lambda m: m.last_activity, reverse=True)

        buckets: dict[str, list[ConversationMetadata]] = {b: [] for b in _DATE_BUCKETS}
        for meta in all_items:
            bucket = meta.date_bucket()
            if meta.pinned:
                buckets["Today"].insert(0, meta)
            else:
                buckets.setdefault(bucket, []).append(meta)

        for bucket in _DATE_BUCKETS:
            items = buckets.get(bucket, [])
            if not items:
                continue
            self._section_headers[bucket].pack(fill="x", pady=(8, 0))
            self._section_frames[bucket].pack(fill="x")
            for meta in items:
                row = _ConversationRow(
                    self._section_frames[bucket],
                    meta,
                    on_select=self._on_select,
                    on_delete=self._on_delete,
                    active=meta.session_id == self._active_sid,
                )
                row.pack(fill="x", pady=2)
                self._rows[meta.session_id] = row
