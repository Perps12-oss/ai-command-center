"""ExecutionTimelineView — full-page chronological execution event browser."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.execution_timeline_list import ExecutionTimelineList
from ai_command_center.ui.design_system import theme_v2 as T


class ExecutionTimelineView(ctk.CTkFrame):
    """Pure display workspace page for execution events."""

    def __init__(
        self,
        master: Any,
        *,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_inspect_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._count = 0
        self._build(on_inspect_select=on_inspect_select, on_inspect_navigate=on_inspect_navigate)

    def _build(
        self,
        *,
        on_inspect_select: Callable[[InspectableRef], None] | None,
        on_inspect_navigate: Callable[[InspectableRef], None] | None,
    ) -> None:
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)

        self._title = ctk.CTkLabel(
            header,
            text="Execution Timeline",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title.pack(side="left", padx=T.PAD, pady=12)

        self._count_label = ctk.CTkLabel(
            header,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._count_label.pack(side="right", padx=T.PAD, pady=12)

        self._scroll = ctk.CTkFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        self._events_list = ExecutionTimelineList(
            self._scroll,
            on_select=on_inspect_select,
            on_navigate=on_inspect_navigate,
        )
        self._events_list.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)
        self._render_title()

    def _render_title(self) -> None:
        self._count_label.configure(
            text=f"{self._count} event{'s' if self._count != 1 else ''}"
        )

    def apply_state(self, events: Sequence[ExecutionEvent]) -> None:
        """Refresh the chronological execution event list."""
        self._count = len(events)
        self._render_title()
        self._events_list.set_events(events)


__all__ = ["ExecutionTimelineView"]
