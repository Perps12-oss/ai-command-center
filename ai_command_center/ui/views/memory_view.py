"""MemoryView — browse, search, and delete stored memories."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T


class _MemoryRow(ctk.CTkFrame):
    """Single memory entry with text, optional timestamp, and delete button."""

    def __init__(
        self,
        master,
        text: str,
        timestamp: str,
        on_delete: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=6,
        )
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        ctk.CTkLabel(
            left,
            text=text,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=500,
            justify="left",
        ).pack(fill="x")

        if timestamp:
            ctk.CTkLabel(
                left,
                text=timestamp,
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

        ctk.CTkButton(
            self,
            text="🗑",
            width=30,
            height=30,
            font=T.FONT_SMALL,
            fg_color="transparent",
            hover_color=T.MSG_ERROR_BG,
            text_color=T.TEXT_MUTED,
            corner_radius=6,
            command=on_delete,
        ).pack(side="right", padx=10, pady=10)


class MemoryView(ctk.CTkFrame):
    """Browse, search, and delete stored memories.

    Architecture contract:
      - load_memories(items) called from app.py via UIQueue.
      - prepend_memory(text, ts) adds a newly stored memory to the top.
      - on_delete(item_id, text) callback fires when user clicks delete.
      - No EventBus or service imports.
    """

    def __init__(
        self,
        master,
        *,
        on_delete: Callable[[str | None, str], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_delete = on_delete
        self._items: list[dict] = []
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(
            self, fg_color=T.BG_PANEL, corner_radius=0, height=44
        )
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Memory",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left", padx=T.PAD, pady=10)

        self._count_lbl = ctk.CTkLabel(
            header, text="", font=T.FONT_SMALL, text_color=T.TEXT_MUTED
        )
        self._count_lbl.pack(side="left", pady=10)

        search_bar = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0)
        search_bar.pack(fill="x")

        self._search = ctk.CTkEntry(
            search_bar,
            placeholder_text="Search memories…",
            font=T.FONT_BODY,
            height=32,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._search.pack(fill="x", padx=T.PAD, pady=(0, 10))
        self._search.bind("<KeyRelease>", lambda _: self._render())

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

        self._render()

    def load_memories(self, items: list[dict]) -> None:
        """Replace the displayed list. items: list of {text, timestamp, id}."""
        self._items = list(items)
        self._render()

    def prepend_memory(self, text: str, timestamp: str = "") -> None:
        """Insert a newly stored memory at the top (no full reload needed)."""
        self._items.insert(0, {"text": text, "timestamp": timestamp, "id": None})
        self._render()

    def _confirm_delete(self, ref: dict) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Delete memory")
        dialog.configure(fg_color=T.BG_PANEL)
        dialog.geometry("360x140")
        dialog.transient(self)
        dialog.grab_set()

        text = str(ref.get("text", ""))[:80]
        ctk.CTkLabel(
            dialog,
            text=f'Delete this memory?\n"{text}"',
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            justify="center",
        ).pack(padx=T.PAD, pady=(16, 12))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(padx=T.PAD, pady=(0, 12))

        def _cancel() -> None:
            dialog.destroy()

        def _confirm() -> None:
            self._items = [it for it in self._items if it is not ref]
            self._on_delete(ref.get("id"), ref.get("text", ""))
            self._render()
            dialog.destroy()

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
            command=_cancel,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row,
            text="Delete",
            font=T.FONT_SMALL,
            fg_color=T.STATUS_ERROR,
            hover_color="#B91C1C",
            text_color="white",
            command=_confirm,
        ).pack(side="left")

    def _visible_items(self) -> list[dict]:
        q = self._search.get().strip().lower()
        if not q:
            return list(self._items)
        return [it for it in self._items if q in it.get("text", "").lower()]

    def _render(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()

        shown = self._visible_items()
        count = len(shown)
        self._count_lbl.configure(
            text=f"  {count} memor{'y' if count == 1 else 'ies'}"
        )

        if not shown:
            msg = (
                'No memories stored yet.\nUse "remember: label | content" to save facts.'
                if not self._items
                else "No memories match your search."
            )
            ctk.CTkLabel(
                self._scroll,
                text=msg,
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
                justify="center",
            ).pack(padx=T.PAD, pady=40)
            return

        for item in shown:
            item_ref = item

            def make_delete(ref=item_ref):
                def _do():
                    self._confirm_delete(ref)
                return _do

            row = _MemoryRow(
                self._scroll,
                item.get("text", ""),
                item.get("timestamp", ""),
                make_delete(),
            )
            row.pack(fill="x", padx=T.PAD, pady=(0, 6))
