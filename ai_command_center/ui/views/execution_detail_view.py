"""ExecutionDetailView — detailed view for a single execution run.

Sections:
  Timeline    — horizontal step timeline
  Scrubber    — execution event index pointer
  TraceTree   — span hierarchy
  Metadata    — key/value attributes grid

Architecture contract: pure display view, no bus/service imports.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.docks.execution_timeline_dock import ExecutionTimelineDock
from ai_command_center.ui.components.trace_tree import TraceTree
from ai_command_center.ui.design_system import theme_v2 as T


class ExecutionDetailView(ctk.CTkFrame):
    """Detailed drill-down view for a single execution run."""

    def __init__(
        self,
        master: Any,
        on_back: Callable[[], None] | None = None,
        on_scrub: Callable[[int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_back = on_back or (lambda: None)
        self._on_scrub = on_scrub or (lambda _index: None)
        self._steps: list[dict[str, Any]] = []
        self._spans: list[Any] = []
        self._timeline_dock: ExecutionTimelineDock | None = None
        self._build()

    def _build(self) -> None:
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

        self._source_lbl = ctk.CTkLabel(
            header,
            text="",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._source_lbl.pack(side="right", padx=T.PAD)

        self._timeline_dock = ExecutionTimelineDock(
            self,
            on_scrub=self._handle_scrub,
        )
        self._timeline_dock.pack(fill="x")

        ctk.CTkLabel(
            self,
            text="TRACE",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._trace_tree = TraceTree(self)
        self._trace_tree.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

        self._meta_frame = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=T.CORNER_RADIUS)
        self._meta_frame.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

    def _handle_scrub(self, index: int) -> None:
        self._on_scrub(index)

    def show_execution(
        self,
        run: Any,
        spans: list[Any] | None = None,
        *,
        timeline_steps: Sequence[dict[str, Any]] | None = None,
        scrub_labels: Sequence[str] | None = None,
        scrub_index: int = 0,
        timeline_source: str = "runs",
    ) -> None:
        """Populate the view from an execution object and optional timeline data."""
        from ai_command_center.domain.trace_span import TraceSpan, build_span_tree

        title = getattr(run, "short_summary", None) or str(getattr(run, "run_id", ""))
        request_id = str(getattr(run, "request_id", "")) or title
        self._title_lbl.configure(text=(title or request_id)[:60])
        self._source_lbl.configure(
            text=f"source: {timeline_source}" if timeline_source else ""
        )

        self._steps = list(timeline_steps or [])
        if not self._steps and spans:
            self._steps = [
                {
                    "name": s.name if isinstance(s, TraceSpan) else str(s.get("name", "")),
                    "status": s.status if isinstance(s, TraceSpan) else str(s.get("status", "ok")),
                    "duration_ms": (
                        s.duration_ms if isinstance(s, TraceSpan) else float(s.get("duration_ms", 0))
                    ),
                }
                for s in spans
            ]

        active_index = 0
        if self._timeline_dock is not None:
            active_index = self._timeline_dock.render(
                self._steps,
                scrub_labels=scrub_labels,
                scrub_index=scrub_index,
            )

        self._spans = list(spans or [])
        if self._spans:
            if isinstance(self._spans[0], TraceSpan):
                roots = build_span_tree(list(self._spans))
            else:
                roots = build_span_tree([TraceSpan.from_dict(s) for s in self._spans])
            self._trace_tree.render(roots)
        else:
            self._trace_tree.render([])

        for child in self._meta_frame.winfo_children():
            child.destroy()
        meta_items: list[tuple[str, str]] = [
            ("Request ID", request_id),
            ("Run ID", str(getattr(run, "run_id", ""))),
            ("Source", str(getattr(run, "source", ""))),
            ("Status", str(getattr(run, "status", ""))),
            ("Provider", str(getattr(run, "provider_id", ""))),
            ("Model", str(getattr(run, "model", ""))),
            ("Timeline", timeline_source),
        ]
        if self._steps and active_index < len(self._steps):
            step = self._steps[active_index]
            for key, value in step.get("detail", {}).items():
                if value:
                    meta_items.append((str(key), str(value)[:120]))
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
