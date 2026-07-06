"""ExecutionDetailView — detailed view for a single execution run.

Sections:
  Timeline    — horizontal step timeline
  TraceTree   — span hierarchy
  Metadata    — key/value attributes grid
  Raw         — JSON payload viewer

Architecture contract: pure display view, no bus/service imports.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.timeline_renderer import TimelineRenderer
from ai_command_center.ui.components.trace_tree import TraceTree
from ai_command_center.ui.design_system import theme_v2 as T


class ExecutionDetailView(ctk.CTkFrame):
    """Detailed drill-down view for a single execution run."""

    def __init__(
        self,
        master: Any,
        on_back: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_back = on_back or (lambda: None)
        self._build()

    def _build(self) -> None:
        # Header bar
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=46)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkButton(
            header,
            text="← Back",
            width=60, height=28,
            font=(T.FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=T.BG_GLASS,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
            command=self._on_back,
        ).pack(side="left", padx=8, pady=9)

        self._title_lbl = ctk.CTkLabel(
            header,
            text="Execution Detail",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title_lbl.pack(side="left", padx=6)

        # Timeline section
        timeline_label = ctk.CTkLabel(
            self,
            text="TIMELINE",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        timeline_label.pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._timeline = TimelineRenderer(self, height=98)
        self._timeline.pack(fill="x", padx=T.PAD)

        # Trace section
        ctk.CTkLabel(
            self,
            text="TRACE",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._trace_tree = TraceTree(self)
        self._trace_tree.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

        # Metadata panel
        self._meta_frame = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=T.CORNER_RADIUS)
        self._meta_frame.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

    def show_execution(self, run: Any, spans: list[Any] | None = None) -> None:
        """Populate the view from an Execution domain object."""
        from ai_command_center.domain.trace_span import TraceSpan, build_span_tree

        title = getattr(run, "short_summary", None) or str(getattr(run, "run_id", ""))
        self._title_lbl.configure(text=title[:60])

        # Build timeline steps from span data or minimal default
        if spans:
            steps = [
                {
                    "name": s.name if isinstance(s, TraceSpan) else str(s.get("name", "")),
                    "status": s.status if isinstance(s, TraceSpan) else str(s.get("status", "ok")),
                    "duration_ms": s.duration_ms if isinstance(s, TraceSpan) else float(s.get("duration_ms", 0)),
                }
                for s in spans
            ]
            self._timeline.render(steps)

            if isinstance(spans[0], TraceSpan):
                roots = build_span_tree(list(spans))
            else:
                roots = build_span_tree([TraceSpan.from_dict(s) for s in spans])
            self._trace_tree.render(roots)
        else:
            self._timeline.render([])
            self._trace_tree.render([])

        # Metadata
        for child in self._meta_frame.winfo_children():
            child.destroy()
        meta_items: list[tuple[str, str]] = [
            ("Run ID", str(getattr(run, "run_id", ""))),
            ("Source", str(getattr(run, "source", ""))),
            ("Status", str(getattr(run, "status", ""))),
            ("Provider", str(getattr(run, "provider_id", ""))),
            ("Model", str(getattr(run, "model", ""))),
        ]
        for label, value in meta_items:
            if not value:
                continue
            row = ctk.CTkFrame(self._meta_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(
                row,
                text=label,
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
                width=80,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=value,
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(side="left", padx=(4, 0))
