"""Execution timeline AppState projection tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_EVENT_APPENDED,
    EXECUTION_EVENTS_LOADED,
)
from ai_command_center.domain.execution_event import ExecutionEvent


def _event(index: int, *, request_id: str = "req-1") -> ExecutionEvent:
    return ExecutionEvent(
        event_id=f"evt-{index}",
        trace_id=f"trace-{index // 10}",
        parent_event_id=f"evt-{index - 1}" if index else None,
        timestamp=float(index),
        event_type=f"event.{index}",
        actor="chat",
        scope="execution",
        request_id=request_id,
        payload=(("index", str(index)), ("kind", "demo")),
    )


def test_execution_timeline_loaded_appended_bounded_and_revisioned() -> None:
    bus = EventBus()
    store = AppStateStore(bus)

    first = _event(1)
    second = _event(2)
    bus.publish(
        EXECUTION_EVENTS_LOADED,
        {"events": [first.to_bus_payload(), second.to_bus_payload()]},
        source="test",
    )
    snap = store.snapshot
    assert snap.execution_timeline.revision == 1
    assert snap.execution_timeline.events == (first, second)

    third = _event(3)
    bus.publish(EXECUTION_EVENT_APPENDED, third.to_bus_payload(), source="test")
    snap = store.snapshot
    assert snap.execution_timeline.revision == 2
    assert snap.execution_timeline.events[-1] == third

    loaded = [_event(index) for index in range(205)]
    bus.publish(
        EXECUTION_EVENTS_LOADED,
        {"events": [event.to_bus_payload() for event in loaded]},
        source="test",
    )
    snap = store.snapshot
    assert snap.execution_timeline.revision == 3
    assert len(snap.execution_timeline.events) == 200
    assert snap.execution_timeline.events[0].event_id == "evt-5"
    assert snap.execution_timeline.events[-1].event_id == "evt-204"
