"""Memory detail panel for the Memory workspace."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class MemoryDetail(ctk.CTkFrame):
    """Shows fields for the currently selected memory catalog entry."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.CARD_RADIUS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
            **kwargs,
        )
        self._title = ctk.CTkLabel(
            self,
            text="Memory detail",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title.pack(fill="x", padx=12, pady=(12, 4))

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 12))
        self.clear()

    def clear(self) -> None:
        clear_children(self._body)
        self._title.configure(text="Memory detail")
        ctk.CTkLabel(
            self._body,
            text="Select a memory to inspect.",
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=8, pady=8)

    def show(self, item: dict[str, Any], *, injected: bool = False) -> None:
        clear_children(self._body)
        label = str(item.get("label") or item.get("text") or "Memory")
        self._title.configure(text=label)

        rows = (
            ("ID", str(item.get("id") or item.get("node_id") or "")),
            ("Label", str(item.get("label") or "")),
            ("Content", str(item.get("content") or item.get("text") or "")),
            ("Workspace", str(item.get("workspace_id") or "")),
            ("Entity", str(item.get("entity_id") or "")),
            ("Timestamp", str(item.get("timestamp") or "")),
            ("In context", "yes" if injected else "no"),
        )
        for key, value in rows:
            if not value and key not in {"In context"}:
                continue
            row = ctk.CTkFrame(self._body, fg_color=T.BG_PANEL, corner_radius=T.SMALL_RADIUS)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(
                row,
                text=key,
                font=(T.FONT_FAMILY, 9, "bold"),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                row,
                text=value,
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=360,
            ).pack(fill="x", padx=10, pady=(0, 8))


__all__ = ["MemoryDetail"]
