"""TraceTree — recursive span tree widget for the execution detail view.

Renders a collapsible tree of TraceSpan objects with status, duration,
and attribute display.

Architecture contract: pure display widget, no bus/service imports.
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.trace_span import TraceSpan
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color


class _SpanNode(ctk.CTkFrame):
    """A single collapsible span node in the trace tree."""

    def __init__(
        self,
        master: Any,
        span: TraceSpan,
        indent: int = 0,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        color = status_color(span.status)
        self._expanded = indent == 0  # expand roots by default
        self._span = span

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=(indent * 16, 0))

        if span.children:
            self._expand_btn = ctk.CTkButton(
                header,
                text="▾" if self._expanded else "▸",
                width=18, height=18,
                font=(T.FONT_FAMILY, 9),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=self._toggle,
            )
            self._expand_btn.pack(side="left")
        else:
            ctk.CTkLabel(
                header,
                text=" ",
                width=18,
            ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="●",
            font=(T.FONT_FAMILY, 8),
            text_color=color,
            width=12,
        ).pack(side="left", padx=2)

        ctk.CTkLabel(
            header,
            text=span.name,
            font=("Consolas", 10),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            header,
            text=f"{span.duration_ms:.1f}ms",
            font=("Consolas", 9),
            text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=8)

        ctk.CTkLabel(
            header,
            text=span.kind,
            font=(T.FONT_FAMILY, 8),
            text_color=T.TEXT_MUTED,
        ).pack(side="right")

        # Children container
        self._children_frame = ctk.CTkFrame(self, fg_color="transparent")
        if self._expanded:
            self._children_frame.pack(fill="x")
        self._build_children()

    def _build_children(self) -> None:
        for child_span in self._span.children:
            _SpanNode(
                self._children_frame,
                child_span,
                indent=1,
            ).pack(fill="x", pady=1)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self._children_frame.pack(fill="x")
            self._expand_btn.configure(text="▾")
        else:
            self._children_frame.pack_forget()
            self._expand_btn.configure(text="▸")


class TraceTree(ctk.CTkFrame):
    """Scrollable trace tree for displaying execution span hierarchies."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)

    def render(self, root_spans: list[TraceSpan]) -> None:
        """Render a span forest (list of root spans)."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not root_spans:
            ctk.CTkLabel(
                self._scroll,
                text="No trace spans",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=20)
            return

        for span in root_spans:
            _SpanNode(self._scroll, span, indent=0).pack(
                fill="x", padx=4, pady=2
            )
