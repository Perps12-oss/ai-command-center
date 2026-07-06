"""InspectorTraceTab — execution trace / span tree for the inspector panel.

Reference: Langflow execution trace panel.

Architecture contract: pure display widget, data supplied via update().
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_MONO_FONT = ("Consolas", 10)


class _SpanRow(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        name: str,
        kind: str,
        status: str,
        duration_ms: float,
        indent: int = 0,
    ) -> None:
        bg = T.STATUS_READY_BG if status == "ok" else T.STATUS_ERROR_BG
        super().__init__(master, fg_color=bg, corner_radius=4, height=28)
        self.pack_propagate(False)

        status_color = T.STATUS_READY if status == "ok" else T.STATUS_ERROR
        ctk.CTkLabel(
            self,
            text="●",
            font=(T.FONT_FAMILY, 8),
            text_color=status_color,
            width=12,
        ).pack(side="left", padx=(8 + indent * 16, 4), pady=6)

        ctk.CTkLabel(
            self,
            text=name,
            font=_MONO_FONT,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            self,
            text=f"{duration_ms:.1f}ms",
            font=_MONO_FONT,
            text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=8)

        ctk.CTkLabel(
            self,
            text=kind,
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=4)


class InspectorTraceTab(ctk.CTkFrame):
    """Displays execution trace spans in a tree-like list."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)

        self._empty_lbl = ctk.CTkLabel(
            self._scroll,
            text="No trace data",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._empty_lbl.pack(pady=20)

    def update(self, spans: list[dict]) -> None:
        """Refresh the span list from a list of SpanItem-like dicts."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not spans:
            ctk.CTkLabel(
                self._scroll,
                text="No trace data",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=20)
            return

        # Simple flat list — determine indent from parent_id
        span_ids = {s.get("span_id", ""): i for i, s in enumerate(spans)}
        for span in spans:
            indent = 1 if span.get("parent_id") and span.get("parent_id") in span_ids else 0
            _SpanRow(
                self._scroll,
                name=str(span.get("name", "span")),
                kind=str(span.get("kind", "internal")),
                status=str(span.get("status", "ok")),
                duration_ms=float(span.get("duration_ms", 0)),
                indent=indent,
            ).pack(fill="x", padx=4, pady=2)
