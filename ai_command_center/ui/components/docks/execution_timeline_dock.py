"""ExecutionTimelineDock — scrubber + timeline renderer for bottom rails."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.execution_timeline_scrubber import (
    ExecutionTimelineScrubber,
)
from ai_command_center.ui.components.timeline_renderer import TimelineRenderer
from ai_command_center.ui.design_system import theme_v2 as T


class ExecutionTimelineDock(ctk.CTkFrame):
    """Hosts :class:`TimelineRenderer` and :class:`ExecutionTimelineScrubber`.

    Composes the execution replay surface used by detail views and future
    workflow-graph bottom rails. The scrubber degrades gracefully when no
    events are available.
    """

    def __init__(
        self,
        master: Any,
        *,
        on_scrub: Callable[[int], None] | None = None,
        timeline_height: int = 98,
        show_section_labels: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_scrub = on_scrub or (lambda _index: None)
        self._steps: list[dict[str, Any]] = []
        self._build(timeline_height=timeline_height, show_section_labels=show_section_labels)

    def _build(self, *, timeline_height: int, show_section_labels: bool) -> None:
        if show_section_labels:
            ctk.CTkLabel(
                self,
                text="TIMELINE",
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._timeline = TimelineRenderer(self, height=timeline_height)
        self._timeline.pack(fill="x", padx=T.PAD)

        self._scrubber = ExecutionTimelineScrubber(
            self,
            on_scrub=self._handle_scrub,
        )
        self._scrubber.pack(fill="x", padx=T.PAD, pady=(8, 0))

    @property
    def timeline(self) -> TimelineRenderer:
        return self._timeline

    @property
    def scrubber(self) -> ExecutionTimelineScrubber:
        return self._scrubber

    def render(
        self,
        steps: Sequence[dict[str, Any]],
        *,
        scrub_labels: Sequence[str] | None = None,
        scrub_index: int = 0,
    ) -> int:
        """Render timeline steps and sync the scrubber. Returns clamped index."""
        self._steps = list(steps)
        active_index = scrub_index
        if self._steps:
            active_index = max(0, min(scrub_index, len(self._steps) - 1))
            self._timeline.render(self._steps, active_index=active_index)
        else:
            self._timeline.render([])

        labels = list(scrub_labels or [str(step.get("name", "")) for step in self._steps])
        self._scrubber.set_timeline(labels, active_index=active_index)
        return active_index

    def _handle_scrub(self, index: int) -> None:
        if self._steps:
            index = max(0, min(index, len(self._steps) - 1))
            self._timeline.render(self._steps, active_index=index)
        self._on_scrub(index)


__all__ = ["ExecutionTimelineDock"]
