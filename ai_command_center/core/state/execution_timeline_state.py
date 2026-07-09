"""Execution timeline AppState slice for the execution event stream."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    EXECUTION_EVENT_APPENDED,
    EXECUTION_EVENTS_LOADED,
)
from ai_command_center.domain.execution_event import ExecutionEvent

_MAX_EXECUTION_TIMELINE_EVENTS = 200


@dataclass(frozen=True, slots=True)
class ExecutionTimelineState:
    """Append-only projection of the latest execution events."""

    events: tuple[ExecutionEvent, ...] = ()
    revision: int = 0


def _parse_event(payload: dict[str, Any]) -> ExecutionEvent | None:
    event = ExecutionEvent.from_bus_payload(payload)
    if not event.event_id or not event.event_type:
        return None
    return event


def _trim_events(events: tuple[ExecutionEvent, ...]) -> tuple[ExecutionEvent, ...]:
    if len(events) <= _MAX_EXECUTION_TIMELINE_EVENTS:
        return events
    return events[-_MAX_EXECUTION_TIMELINE_EVENTS :]


def _reduce_execution_event_appended(
    state: ExecutionTimelineState,
    event: Event,
) -> ExecutionTimelineState:
    if event.topic != EXECUTION_EVENT_APPENDED:
        return state
    parsed = _parse_event(dict(event.payload or {}))
    if parsed is None:
        return state
    events = _trim_events(state.events + (parsed,))
    if events == state.events:
        return state
    return replace(
        state,
        events=events,
        revision=state.revision + 1,
    )


def _reduce_execution_events_loaded(
    state: ExecutionTimelineState,
    event: Event,
) -> ExecutionTimelineState:
    if event.topic != EXECUTION_EVENTS_LOADED:
        return state
    raw_events = event.payload.get("events") or []
    events: list[ExecutionEvent] = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        parsed = _parse_event(raw)
        if parsed is not None:
            events.append(parsed)
    trimmed = _trim_events(tuple(events))
    if trimmed == state.events:
        return state
    return replace(
        state,
        events=trimmed,
        revision=state.revision + 1,
    )


def reduce_execution_timeline_state(
    state: ExecutionTimelineState,
    event: Event,
) -> ExecutionTimelineState:
    """Pure reducer for execution timeline stream events."""
    if event.topic == EXECUTION_EVENT_APPENDED:
        return _reduce_execution_event_appended(state, event)
    if event.topic == EXECUTION_EVENTS_LOADED:
        return _reduce_execution_events_loaded(state, event)
    return state


__all__ = [
    "ExecutionTimelineState",
    "reduce_execution_timeline_state",
]
