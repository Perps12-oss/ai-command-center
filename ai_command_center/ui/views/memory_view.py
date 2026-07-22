"""MemoryView — Memory workspace: catalog, search, detail, injection, inspector."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.memory.memory_card import MemoryCard
from ai_command_center.ui.components.memory.memory_detail import MemoryDetail
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class MemoryView(ctk.CTkFrame):
    """Browse, search, select, and delete stored memories.

    Architecture contract:
      - ``load_from_appstate(snap)`` projects AppState catalogs.
      - Callbacks publish intents via shell / UIController (no EventBus here).
      - Injection indicator uses ``memory_selected`` and optional context sources.
    """

    def __init__(
        self,
        master: Any,
        *,
        on_delete: Callable[[str | None, str], None],
        on_add: Callable[[str, str], None] | None = None,
        on_select: Callable[[dict[str, Any]], None] | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_search: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_delete = on_delete
        self._on_add = on_add
        self._on_select = on_select
        self._on_inspect_select = on_inspect_select
        self._on_search = on_search
        self._items: list[dict[str, Any]] = []
        self._injected_labels: set[str] = set()
        self._selected_id: str | None = None
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=44)
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

        self._injection_frame = ctk.CTkFrame(header, fg_color="transparent")
        self._injection_frame.pack(side="right", padx=(0, T.PAD), pady=6)

        if self._on_add is not None:
            ctk.CTkButton(
                header,
                text="+ Add",
                width=70,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.ACCENT_DEFAULT,
                hover_color=T.ACCENT_HOVER,
                text_color="white",
                corner_radius=T.SMALL_RADIUS,
                command=self._show_add_dialog,
            ).pack(side="right", padx=T.PAD, pady=8)

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
        self._search.bind("<KeyRelease>", lambda _: self._on_search_key())

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(body, fg_color=T.BG_DEEP, corner_radius=0)
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self._scroll.columnconfigure(0, weight=1)

        self._detail = MemoryDetail(body)
        self._detail.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self._render()

    def update_injection_indicator(self, selected: tuple[str, ...]) -> None:
        """Show badges for memories currently injected into context."""
        self._injected_labels = {str(label) for label in selected if str(label).strip()}
        clear_children(self._injection_frame)
        if not self._injected_labels:
            ctk.CTkLabel(
                self._injection_frame,
                text="No memories in context",
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_MUTED,
            ).pack(side="left")
            self._render()
            return
        ctk.CTkLabel(
            self._injection_frame,
            text="In context:",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(0, 4))
        labels = list(self._injected_labels)
        for label in labels[:4]:
            ctk.CTkLabel(
                self._injection_frame,
                text=label[:24],
                font=(T.FONT_FAMILY, 10),
                text_color=T.STATUS_READY,
                fg_color=T.BG_GLASS,
                corner_radius=T.SMALL_RADIUS,
                padx=6,
                pady=2,
            ).pack(side="left", padx=2)
        if len(labels) > 4:
            ctk.CTkLabel(
                self._injection_frame,
                text=f"+{len(labels) - 4}",
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_MUTED,
            ).pack(side="left", padx=2)
        self._render()

    def load_memories(self, items: list[dict]) -> None:
        """Replace the displayed list. items: list of {text, timestamp, id}."""
        self._items = [self._normalize_item(item) for item in items]
        self._render()

    def load_from_appstate(self, snap: Any) -> None:
        """Render memory catalog from AppState projection."""
        notes_memory = getattr(snap, "notes_memory", None)
        catalog = notes_memory.memory_catalog if notes_memory is not None else snap.memory_catalog
        selected = notes_memory.memory_selected if notes_memory is not None else snap.memory_selected
        context_sources = tuple(getattr(getattr(snap, "global_context", None), "sources", ()) or ())
        items: list[dict[str, Any]] = []
        for item in catalog:
            items.append(
                {
                    "id": getattr(item, "node_id", ""),
                    "node_id": getattr(item, "node_id", ""),
                    "label": getattr(item, "label", ""),
                    "text": getattr(item, "label", ""),
                    "workspace_id": getattr(item, "workspace_id", ""),
                    "entity_id": getattr(item, "entity_id", ""),
                    "timestamp": "",
                    "content": "",
                }
            )
        self._items = items
        injected = tuple(str(x) for x in selected) + tuple(str(x) for x in context_sources)
        self.update_injection_indicator(injected)

    def add_memory(self, payload: dict) -> None:
        """Insert a newly stored memory at the top from a service payload."""
        label = str(payload.get("label", ""))
        content = str(payload.get("content", ""))
        text = f"{label} | {content}" if content else label
        self._items.insert(
            0,
            self._normalize_item(
                {
                    "text": text,
                    "label": label,
                    "content": content,
                    "timestamp": "",
                    "id": payload.get("id"),
                }
            ),
        )
        self._render()

    def prepend_memory(self, text: str, timestamp: str = "") -> None:
        """Insert a newly stored memory at the top (no full reload needed)."""
        self._items.insert(0, self._normalize_item({"text": text, "timestamp": timestamp, "id": None}))
        self._render()

    def show_error(self, message: str) -> None:
        """Surface a transient error in the detail pane."""
        self._detail.show({"label": "Memory error", "content": message})

    @staticmethod
    def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
        out = dict(item)
        label = str(out.get("label") or "")
        text = str(out.get("text") or "")
        if not label and text:
            out["label"] = text.split(" | ", 1)[0].strip() or text
        if not out.get("id") and out.get("node_id"):
            out["id"] = out["node_id"]
        if not out.get("node_id") and out.get("id"):
            out["node_id"] = out["id"]
        return out

    def _is_injected(self, item: dict[str, Any]) -> bool:
        label = str(item.get("label") or item.get("text") or "")
        if not label:
            return False
        if label in self._injected_labels:
            return True
        return any(label in src or src in label for src in self._injected_labels)

    def _show_add_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add memory")
        dialog.configure(fg_color=T.BG_PANEL)
        dialog.geometry("420x220")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Label", font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 2))
        label_entry = ctk.CTkEntry(
            dialog,
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        label_entry.pack(fill="x", padx=T.PAD)

        ctk.CTkLabel(
            dialog, text="Content", font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=T.PAD, pady=(8, 2))
        content_entry = ctk.CTkEntry(
            dialog,
            font=T.FONT_BODY,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        content_entry.pack(fill="x", padx=T.PAD)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(padx=T.PAD, pady=(16, 12))

        def _cancel() -> None:
            dialog.destroy()

        def _confirm() -> None:
            label = label_entry.get().strip()
            content = content_entry.get().strip()
            if label and content and self._on_add is not None:
                self._on_add(label, content)
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
            text="Save",
            font=T.FONT_SMALL,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="white",
            command=_confirm,
        ).pack(side="left")

    def _confirm_delete(self, ref: dict[str, Any]) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Delete memory")
        dialog.configure(fg_color=T.BG_PANEL)
        dialog.geometry("360x140")
        dialog.transient(self)
        dialog.grab_set()

        text = str(ref.get("label") or ref.get("text", ""))[:80]
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
            if self._selected_id and str(ref.get("id") or "") == self._selected_id:
                self._selected_id = None
                self._detail.clear()
            self._on_delete(ref.get("id"), str(ref.get("text") or ref.get("label") or ""))
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

    def _on_search_key(self) -> None:
        query = self._search.get().strip()
        if self._on_search is not None:
            self._on_search(query)
        self._render()

    def _visible_items(self) -> list[dict[str, Any]]:
        q = self._search.get().strip().lower()
        if not q:
            return list(self._items)
        return [
            it
            for it in self._items
            if q in str(it.get("text", "")).lower()
            or q in str(it.get("label", "")).lower()
            or q in str(it.get("content", "")).lower()
        ]

    def _handle_select(self, item: dict[str, Any]) -> None:
        self._selected_id = str(item.get("id") or item.get("node_id") or "") or None
        injected = self._is_injected(item)
        self._detail.show(item, injected=injected)
        self._render()
        if self._on_select is not None:
            self._on_select(item)
        if self._on_inspect_select is not None:
            ref_id = str(item.get("id") or item.get("node_id") or item.get("label") or "memory")
            label = str(item.get("label") or item.get("text") or ref_id)
            payload = tuple(
                (str(k), str(v))
                for k, v in item.items()
                if v is not None and str(v) != ""
            )
            self._on_inspect_select(
                InspectableRef(kind="memory", ref_id=ref_id, label=label, payload=payload)
            )

    def _render(self) -> None:
        clear_children(self._scroll)
        shown = self._visible_items()
        count = len(shown)
        self._count_lbl.configure(text=f"  {count} memor{'y' if count == 1 else 'ies'}")

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
            item_id = str(item.get("id") or item.get("node_id") or "")
            card = MemoryCard(
                self._scroll,
                item=item,
                selected=bool(self._selected_id and item_id == self._selected_id),
                injected=self._is_injected(item),
                on_select=self._handle_select,
                on_delete=self._confirm_delete,
            )
            card.pack(fill="x", padx=T.PAD, pady=(0, 6))
