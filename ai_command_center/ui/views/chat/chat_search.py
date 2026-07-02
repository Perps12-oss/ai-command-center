"""In-conversation search bar and matching logic."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class SearchBar(ctk.CTkFrame):
    """Slide-in search bar for finding text in chat history (Ctrl+F)."""

    def __init__(self, master, on_search: Callable[[str], None], on_close: Callable) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=0,
            height=38,
        )
        self.pack_propagate(False)
        self._on_search = on_search
        self._on_close = on_close

        self._entry = ctk.CTkEntry(
            self,
            placeholder_text="Search messages…",
            font=T.FONT_BODY,
            height=26,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
            width=220,
        )
        self._entry.pack(side="left", padx=(12, 4), pady=6)
        self._entry.bind("<KeyRelease>", lambda _e: self._on_search(self._entry.get()))
        self._entry.bind("<Escape>", lambda _e: self._on_close())

        self._count_lbl = ctk.CTkLabel(
            self, text="", font=T.FONT_SMALL, text_color=T.TEXT_MUTED
        )
        self._count_lbl.pack(side="left", padx=4)

        ctk.CTkButton(
            self, text="✕", width=24, height=24,
            font=T.FONT_SMALL,
            fg_color="transparent", hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED, corner_radius=T.SMALL_RADIUS,
            command=self._on_close,
        ).pack(side="right", padx=8)

    def focus(self) -> None:
        self._entry.focus_set()
        self._entry.select_range(0, "end")

    def set_count(self, found: int, total: int) -> None:
        if total == 0:
            self._count_lbl.configure(text="No matches", text_color=T.STATUS_ERROR)
        else:
            self._count_lbl.configure(
                text=f"{found}/{total}", text_color=T.TEXT_MUTED
            )

    def get_query(self) -> str:
        return self._entry.get()


class ChatSearchController:
    """Manages search bar visibility, keyboard shortcut, and scroll-to-match."""

    def __init__(
        self,
        master,
        session_bar,
        scroll,
        get_history: Callable[[], list[dict]],
    ) -> None:
        self._master = master
        self._session_bar = session_bar
        self._scroll = scroll
        self._get_history = get_history
        self._visible = False
        self._bar = SearchBar(master, on_search=self.do_search, on_close=self.close)

    @property
    def bar(self) -> SearchBar:
        return self._bar

    def bind_shortcuts(self, root) -> None:
        root.bind("<Control-f>", lambda _e: self.toggle(), add="+")
        root.bind("<Control-F>", lambda _e: self.toggle(), add="+")

    def toggle(self) -> None:
        if self._visible:
            self.close()
        else:
            self._visible = True
            self._bar.pack(fill="x", side="top", after=self._session_bar)
            self._bar.focus()

    def close(self) -> None:
        self._visible = False
        self._bar.pack_forget()
        self.do_search("")

    def do_search(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            self._bar.set_count(0, 0)
            return
        matches = sum(
            1 for msg in self._get_history()
            if q in str(msg.get("content", "")).lower()
        )
        self._bar.set_count(matches, matches)
        for widget in self._scroll.winfo_children():
            if not hasattr(widget, "winfo_children"):
                continue
            for child in widget.winfo_children():
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, ctk.CTkTextbox):
                        try:
                            txt = grandchild.get("1.0", "end-1c").lower()
                            if q in txt:
                                self._scroll._parent_canvas.yview_moveto(
                                    widget.winfo_y() / max(self._scroll.winfo_height(), 1)
                                )
                                return
                        except Exception:
                            pass
