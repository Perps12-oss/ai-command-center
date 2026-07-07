"""Shared payload-rendering inspector base."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.design_system import theme_v2 as T

_DEFAULT_PREVIEW_KEYS = ("content", "text", "body", "description", "summary")


class PayloadInspector(BaseInspector):
    """Base inspector that renders a single payload as key/value rows."""

    def __init__(self, master: Any, *, fallback_title: str, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._fallback_title = fallback_title
        self._title = ctk.CTkLabel(
            self,
            text=fallback_title,
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

    def preview_keys(self) -> tuple[str, ...]:
        return _DEFAULT_PREVIEW_KEYS

    def empty_message(self) -> str:
        return "No payload available."

    def preview_label(self) -> str:
        return "Preview"

    def update(self, ref: InspectableRef) -> None:
        self._clear()
        header = ref.label or ref.kind.title() or self._fallback_title
        self._title.configure(text=header)

        if not ref.payload:
            ctk.CTkLabel(
                self._body,
                text=self.empty_message(),
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=8, pady=8)
            return

        payload = dict(ref.payload)
        preview = ""
        for key in self.preview_keys():
            value = payload.get(key)
            if value:
                preview = str(value)
                break

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

        if preview:
            preview_text = preview if len(preview) <= 400 else preview[:397] + "…"
            preview_box = ctk.CTkFrame(self._body, fg_color=T.BG_PANEL, corner_radius=T.SMALL_RADIUS)
            preview_box.pack(fill="x", padx=8, pady=(8, 4))
            ctk.CTkLabel(
                preview_box,
                text=self.preview_label(),
                font=(T.FONT_FAMILY, 9, "bold"),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                preview_box,
                text=preview_text,
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=360,
            ).pack(fill="x", padx=10, pady=(0, 8))


__all__ = ["PayloadInspector"]
