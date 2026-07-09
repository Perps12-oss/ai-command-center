"""Execution event AppState reducer tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_EVENT_APPENDED,
    EXECUTION_EVENTS_LOADED,
    EXECUTION_QUERY_RESULT,
    UI_EXECUTION_TIMELINE_SCRUB,
)
from ai_command_center.core.state.execution_event_state import (
    ExecutionEventItem,
    execution_events_for_request,
)


def test_execution_events_for_request_filters_by_request_id() -> None:
    catalog = (
        ExecutionEventItem(event_id="e1", request_id="req-1", event_type="chat.started"),
        ExecutionEventItem(event_id="e2", request_id="req-2", event_type="tool.started"),
        ExecutionEventItem(event_id="e3", request_id="req-1", event_type="chat.complete"),
    )
    scoped = execution_events_for_request(catalog, "req-1")
    assert [item.event_id for item in scoped] == ["e1", "e3"]


def test_execution_event_appended_projects_catalog() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            EXECUTION_EVENT_APPENDED,
            {
                "event_id": "evt-1",
                "trace_id": "trace-1",
                "event_type": "chat.complete",
                "actor": "chat",
                "scope": "chat",
                "request_id": "req-1",
                "payload": {"text": "hello"},
            },
            source="test",
        )
        snap = store.snapshot
        assert len(snap.recent_execution_events) == 1
        assert snap.recent_execution_events[0].event_id == "evt-1"
        assert snap.execution_timeline.request_id == "req-1"
    finally:
        store.close()


def test_execution_query_result_sets_timeline() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            EXECUTION_QUERY_RESULT,
            {
                "request_id": "req-9",
                "timeline_source": "events",
                "execution_events": [
                    {
                        "event_id": "evt-a",
                        "trace_id": "trace-9",
                        "event_type": "chat.started",
                        "actor": "chat",
                        "scope": "chat",
                        "request_id": "req-9",
                        "payload": {},
                    },
                    {
                        "event_id": "evt-b",
                        "trace_id": "trace-9",
                        "event_type": "chat.complete",
                        "actor": "chat",
                        "scope": "chat",
                        "request_id": "req-9",
                        "payload": {"text": "done"},
                    },
                ],
            },
            source="test",
        )
        snap = store.snapshot
        assert snap.execution_timeline.request_id == "req-9"
        assert len(snap.execution_timeline.events) == 2
        assert snap.execution_timeline.scrub_index == 1
        assert snap.execution_timeline.source == "events"
    finally:
        store.close()


def test_execution_timeline_scrub_updates_index() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            EXECUTION_QUERY_RESULT,
            {
                "request_id": "req-9",
                "execution_events": [
                    {
                        "event_id": "evt-a",
                        "event_type": "chat.started",
                        "request_id": "req-9",
                        "payload": {},
                    },
                    {
                        "event_id": "evt-b",
                        "event_type": "chat.complete",
                        "request_id": "req-9",
                        "payload": {},
                    },
                ],
            },
            source="test",
        )
        bus.publish(
            UI_EXECUTION_TIMELINE_SCRUB,
            {"request_id": "req-9", "index": 0},
            source="ui",
        )
        snap = store.snapshot
        assert snap.execution_timeline.scrub_index == 0
    finally:
        store.close()


def test_execution_events_loaded_replaces_catalog() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            EXECUTION_EVENTS_LOADED,
            {
                "events": [
                    {
                        "event_id": "seed-1",
                        "event_type": "tool.result",
                        "request_id": "req-seed",
                        "payload": {},
                    }
                ]
            },
            source="test",
        )
        snap = store.snapshot
        assert snap.recent_execution_events[0].event_id == "seed-1"
    finally:
        store.close()
