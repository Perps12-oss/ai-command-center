"""Memory catalog card for the Memory workspace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class MemoryCard(ctk.CTkFrame):
    """Selectable memory row with optional injection badge and delete action."""

    def __init__(
        self,
        master: Any,
        *,
        item: dict[str, Any],
        selected: bool = False,
        injected: bool = False,
        on_select: Callable[[dict[str, Any]], None] | None = None,
        on_delete: Callable[[dict[str, Any]], None] | None = None,
        **kwargs: Any,
    ) -> None:
        fg = T.HERO_CYAN_DIM if selected else T.BG_GLASS
        super().__init__(
            master,
            fg_color=fg,
            border_color=T.HERO_CYAN if selected else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        self._item = item
        self._on_select = on_select
        self._on_delete = on_delete

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        title = str(item.get("label") or item.get("text") or item.get("id") or "Memory")
        ctk.CTkLabel(
            left,
            text=title,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=420,
            justify="left",
        ).pack(fill="x")

        meta_parts: list[str] = []
        if item.get("timestamp"):
            meta_parts.append(str(item["timestamp"]))
        if item.get("workspace_id"):
            meta_parts.append(f"ws:{item['workspace_id']}")
        if injected:
            meta_parts.append("in context")
        if meta_parts:
            ctk.CTkLabel(
                left,
                text=" · ".join(meta_parts),
                font=(T.FONT_FAMILY, 10),
                text_color=T.STATUS_READY if injected else T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

        if on_delete is not None:
            ctk.CTkButton(
                self,
                text="🗑",
                width=30,
                height=30,
                font=T.FONT_SMALL,
                fg_color="transparent",
                hover_color=T.MSG_ERROR_BG,
                text_color=T.TEXT_MUTED,
                corner_radius=T.SMALL_RADIUS,
                command=lambda: on_delete(item),
            ).pack(side="right", padx=10, pady=10)

        self.bind("<Button-1>", self._handle_select)
        left.bind("<Button-1>", self._handle_select)
        for child in left.winfo_children():
            try:
                child.bind("<Button-1>", self._handle_select)
            except Exception:
                pass

    def _handle_select(self, _event: Any = None) -> None:
        if self._on_select is not None:
            self._on_select(self._item)


__all__ = ["MemoryCard"]
