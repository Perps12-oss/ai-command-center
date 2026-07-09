"""Compact execution-event list with inspect gestures."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector.inspect_gestures import bind_inspect_gestures
from ai_command_center.ui.design_system import theme_v2 as T

_MONO_FONT = ("Consolas", 10)


def _format_timestamp(timestamp: float) -> str:
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime("%H:%M:%S")
    except Exception:
        return "--:--:--"


def _payload_summary(event: ExecutionEvent, *, limit: int = 4) -> str:
    payload = event.payload_dict()
    if not payload:
        return "payload: —"
    items = list(payload.items())[:limit]
    summary = ", ".join(f"{key}={value}" for key, value in items)
    if len(payload) > limit:
        summary = f"{summary}, …"
    return f"payload: {summary}"


def _event_ref(event: ExecutionEvent) -> InspectableRef:
    return InspectableRef.from_payload(
        {
            "kind": "execution",
            "ref_id": event.event_id,
            "label": event.event_type or event.event_id,
            "payload": event.to_bus_payload(),
        }
    )


class _TimelineRow(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        event: ExecutionEvent,
        *,
        on_select: Callable[[InspectableRef], None] | None,
        on_navigate: Callable[[InspectableRef], None] | None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
        )
        ref = _event_ref(event)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 0))

        ts_lbl = ctk.CTkLabel(
            top,
            text=_format_timestamp(event.timestamp),
            font=_MONO_FONT,
            text_color=T.TEXT_MUTED,
        )
        ts_lbl.pack(side="left")

        type_lbl = ctk.CTkLabel(
            top,
            text=event.event_type or "execution.event",
            font=(T.FONT_FAMILY, 10, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        type_lbl.pack(side="left", padx=(8, 0), fill="x", expand=True)

        actor_lbl = ctk.CTkLabel(
            top,
            text=event.actor or "actor",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_SECONDARY,
        )
        actor_lbl.pack(side="right")

        meta = ctk.CTkLabel(
            self,
            text=(
                f"actor={event.actor or '—'} · "
                f"scope={event.scope or '—'} · "
                f"request={event.request_id or '—'}"
            ),
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        meta.pack(fill="x", padx=8, pady=(2, 0))

        payload = ctk.CTkLabel(
            self,
            text=_payload_summary(event),
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=520,
        )
        payload.pack(fill="x", padx=8, pady=(0, 6))

        bind_inspect_gestures(
            (self, top, ts_lbl, type_lbl, actor_lbl, meta, payload),
            get_ref=lambda ref=ref: ref,
            on_select=on_select,
            on_navigate=on_navigate,
        )


class ExecutionTimelineList(ctk.CTkScrollableFrame):
    """Scrollable chronological event list for execution timelines."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[InspectableRef], None] | None = None,
        on_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", corner_radius=0, **kwargs)
        self._on_select = on_select
        self._on_navigate = on_navigate
        self._events: tuple[ExecutionEvent, ...] = ()

    def set_events(self, events: Sequence[ExecutionEvent]) -> None:
        self._events = tuple(events)
        self._render()

    def _render(self) -> None:
        for child in self.winfo_children():
            child.destroy()

        if not self._events:
            ctk.CTkLabel(
                self,
                text="No execution events",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=20)
            return

        for event in self._events:
            _TimelineRow(
                self,
                event,
                on_select=self._on_select,
                on_navigate=self._on_navigate,
            ).pack(fill="x", padx=4, pady=3)


__all__ = ["ExecutionTimelineList"]
