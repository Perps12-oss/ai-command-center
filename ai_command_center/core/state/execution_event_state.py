"""Execution event AppState reducers (ACC UI Refurbishment PR 9)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    EXECUTION_EVENT_APPENDED,
    EXECUTION_EVENTS_LOADED,
    EXECUTION_QUERY_RESULT,
    UI_EXECUTION_TIMELINE_SCRUB,
)
from ai_command_center.domain.execution_event import ExecutionEvent

_MAX_EVENTS = 100


@dataclass(frozen=True, slots=True)
class ExecutionEventItem:
    """AppState projection for execution timeline stream entries."""

    event_id: str = ""
    trace_id: str = ""
    parent_event_id: str = ""
    timestamp: float = 0.0
    event_type: str = ""
    actor: str = ""
    scope: str = ""
    request_id: str = ""
    payload: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_event(cls, event: ExecutionEvent) -> ExecutionEventItem:
        return cls(
            event_id=event.event_id,
            trace_id=event.trace_id,
            parent_event_id=event.parent_event_id or "",
            timestamp=event.timestamp,
            event_type=event.event_type,
            actor=event.actor,
            scope=event.scope,
            request_id=event.request_id,
            payload=event.payload,
        )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ExecutionEventItem:
        return cls.from_event(ExecutionEvent.from_bus_payload(payload))


@dataclass(frozen=True, slots=True)
class ExecutionTimelineState:
    """Active execution timeline for scrubber + detail view."""

    request_id: str = ""
    events: tuple[ExecutionEventItem, ...] = ()
    scrub_index: int = 0
    source: str = "runs"


def execution_events_for_request(
    catalog: tuple[ExecutionEventItem, ...],
    request_id: str,
) -> tuple[ExecutionEventItem, ...]:
    """Return execution events scoped to a request id."""
    rid = str(request_id or "").strip()
    if not rid:
        return ()
    return tuple(item for item in catalog if item.request_id == rid)


def _parse_events(payload: dict[str, Any]) -> tuple[ExecutionEventItem, ...]:
    raw = payload.get("execution_events") or payload.get("events") or []
    items: list[ExecutionEventItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        item = ExecutionEventItem.from_payload(entry)
        if item.event_id:
            items.append(item)
    return tuple(items)


def _upsert_events(
    catalog: tuple[ExecutionEventItem, ...],
    item: ExecutionEventItem,
) -> tuple[ExecutionEventItem, ...]:
    filtered = tuple(event for event in catalog if event.event_id != item.event_id)
    updated = (item,) + filtered
    if len(updated) > _MAX_EVENTS:
        updated = updated[:_MAX_EVENTS]
    return updated


def _reduce_execution_event_appended(state: Any, event: Event) -> Any:
    if event.topic != EXECUTION_EVENT_APPENDED:
        return state
    item = ExecutionEventItem.from_payload(event.payload)
    if not item.event_id:
        return state
    timeline = state.execution_timeline
    if item.request_id and (
        not timeline.request_id or timeline.request_id == item.request_id
    ):
        base_events = timeline.events if timeline.request_id == item.request_id else ()
        events = _upsert_events(base_events, item)
        scrub_index = len(events) - 1 if events else 0
        timeline = ExecutionTimelineState(
            request_id=item.request_id,
            events=events,
            scrub_index=scrub_index,
            source="events",
        )
    return replace(
        state,
        recent_execution_events=_upsert_events(state.recent_execution_events, item),
        execution_timeline=timeline,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_execution_events_loaded(state: Any, event: Event) -> Any:
    if event.topic != EXECUTION_EVENTS_LOADED:
        return state
    catalog = _parse_events(event.payload)
    if not catalog:
        return state
    return replace(
        state,
        recent_execution_events=catalog[-_MAX_EVENTS:],
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_execution_query_timeline(state: Any, event: Event) -> Any:
    if event.topic != EXECUTION_QUERY_RESULT:
        return state
    request_id = str(event.payload.get("request_id", "")).strip()
    events = _parse_events(event.payload)
    scrub_index = len(events) - 1 if events else 0
    return replace(
        state,
        execution_timeline=ExecutionTimelineState(
            request_id=request_id,
            events=events,
            scrub_index=scrub_index,
            source=str(event.payload.get("timeline_source", "runs")),
        ),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_execution_timeline_scrub(state: Any, event: Event) -> Any:
    if event.topic != UI_EXECUTION_TIMELINE_SCRUB:
        return state
    request_id = str(event.payload.get("request_id", "")).strip()
    if request_id and request_id != state.execution_timeline.request_id:
        return state
    try:
        index = int(event.payload.get("index", 0))
    except (TypeError, ValueError):
        return state
    events = state.execution_timeline.events
    if not events:
        return state
    index = max(0, min(index, len(events) - 1))
    return replace(
        state,
        execution_timeline=replace(state.execution_timeline, scrub_index=index),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


EXECUTION_EVENT_REDUCERS: tuple[Any, ...] = (
    _reduce_execution_event_appended,
    _reduce_execution_events_loaded,
    _reduce_execution_query_timeline,
    _reduce_execution_timeline_scrub,
)

__all__ = [
    "EXECUTION_EVENT_REDUCERS",
    "ExecutionEventItem",
    "ExecutionTimelineState",
    "execution_events_for_request",
]
