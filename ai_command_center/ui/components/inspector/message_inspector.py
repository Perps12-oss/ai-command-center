"""Message inspector widget."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.design_system import theme_v2 as T


class MessageInspector(BaseInspector):
    """Renders a message inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._title = ctk.CTkLabel(
            self,
            text="Message",
            font=(T.FONT_FAMILY, 12, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title.pack(fill="x", padx=12, pady=(12, 8))

        self._body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _clear(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()

    def update(self, ref: InspectableRef) -> None:
        self._clear()
        header = ref.label or ref.kind.title() or "Message"
        self._title.configure(text=header)

        if not ref.payload:
            ctk.CTkLabel(
                self._body,
                text="No payload available.",
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=8, pady=8)
            return

        payload = dict(ref.payload)
        content = str(payload.get("content") or payload.get("text") or payload.get("body") or "")

        for key, value in ref.payload:
            row = ctk.CTkFrame(self._body, fg_color=T.BG_GLASS, corner_radius=T.SMALL_RADIUS)
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

        if content:
            preview = content if len(content) <= 400 else content[:397] + "…"
            preview_box = ctk.CTkFrame(self._body, fg_color=T.BG_PANEL, corner_radius=T.SMALL_RADIUS)
            preview_box.pack(fill="x", padx=8, pady=(8, 4))
            ctk.CTkLabel(
                preview_box,
                text="Preview",
                font=(T.FONT_FAMILY, 9, "bold"),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                preview_box,
                text=preview,
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=360,
            ).pack(fill="x", padx=10, pady=(0, 8))


__all__ = ["MessageInspector"]
