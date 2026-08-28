from __future__ import annotations

import time

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    APP_ERROR,
    UI_COMMAND,
    UI_CREATE_WORKSPACE,
    UI_WORKSPACE_REQUIRED,
    WORKSPACE_ACTIVE,
    WORKSPACE_CREATE_RESULT,
)
from ai_command_center.services.workspace_bootstrap_service import WorkspaceBootstrapService


def _create_result(bus: EventBus, create_payload: dict[str, object], workspace_id: str) -> None:
    """Mimic the entity handler: activate, then echo the correlated result."""
    bus.publish(WORKSPACE_ACTIVE, {"workspace_id": workspace_id}, source="test")
    bus.publish(
        WORKSPACE_CREATE_RESULT,
        {
            "request_id": "rq-1",
            "workspace_id": workspace_id,
            "bootstrap_id": create_payload.get("bootstrap_id", ""),
        },
        source="test",
    )


def test_workspace_bootstrap_creates_workspace_then_replays_command() -> None:
    bus = EventBus()
    service = WorkspaceBootstrapService(bus)
    create_events: list[dict[str, object]] = []
    command_events: list[dict[str, object]] = []
    bus.subscribe(UI_CREATE_WORKSPACE, lambda e: create_events.append(dict(e.payload)))
    bus.subscribe(UI_COMMAND, lambda e: command_events.append(dict(e.payload)))
    service.start()
    try:
        bus.publish(
            UI_WORKSPACE_REQUIRED,
            {"request_id": "req-1", "text": "> echo hello"},
            source="test",
        )
        assert len(create_events) == 1
        assert create_events[0]["bootstrap_id"]
        assert not command_events

        _create_result(bus, create_events[0], "ws-1")
        assert len(command_events) == 1
        assert command_events[0]["text"] == "> echo hello"
        assert command_events[0]["request_id"] == "req-1"
        assert command_events[0]["replayed_from_workspace_bootstrap"] is True
        assert command_events[0]["bootstrap_workspace_id"] == "ws-1"
        assert not service.bootstrap_inflight
    finally:
        service.stop()


def test_workspace_bootstrap_replays_immediately_when_workspace_active() -> None:
    bus = EventBus()
    service = WorkspaceBootstrapService(bus)
    create_events: list[dict[str, object]] = []
    command_events: list[dict[str, object]] = []
    bus.subscribe(UI_CREATE_WORKSPACE, lambda e: create_events.append(dict(e.payload)))
    bus.subscribe(UI_COMMAND, lambda e: command_events.append(dict(e.payload)))
    service.start()
    try:
        bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-1"}, source="test")
        bus.publish(
            UI_WORKSPACE_REQUIRED,
            {"request_id": "req-2", "text": "> echo now"},
            source="test",
        )
        assert not create_events
        assert len(command_events) == 1
        assert command_events[0]["text"] == "> echo now"
    finally:
        service.stop()


def test_creation_failure_clears_latch_and_reports_failure() -> None:
    bus = EventBus()
    service = WorkspaceBootstrapService(bus)
    create_events: list[dict[str, object]] = []
    command_events: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    bus.subscribe(UI_CREATE_WORKSPACE, lambda e: create_events.append(dict(e.payload)))
    bus.subscribe(UI_COMMAND, lambda e: command_events.append(dict(e.payload)))
    bus.subscribe(APP_ERROR, lambda e: errors.append(dict(e.payload)))
    service.start()
    try:
        bus.publish(
            UI_WORKSPACE_REQUIRED,
            {"request_id": "req-3", "text": "note this down"},
            source="test",
        )
        bus.publish(
            WORKSPACE_CREATE_RESULT,
            {
                "request_id": "rq-1",
                "error": "disk full",
                "bootstrap_id": create_events[0]["bootstrap_id"],
            },
            source="test",
        )

        assert not service.bootstrap_inflight
        assert service.pending_command_count == 0
        assert errors and "disk full" in str(errors[-1]["message"])
        assert errors[-1]["request_id"] == "req-3"

        # Latch cleared: a second required-command starts a *new* attempt.
        bus.publish(
            UI_WORKSPACE_REQUIRED,
            {"request_id": "req-4", "text": "note this down"},
            source="test",
        )
        assert len(create_events) == 2
        assert create_events[1]["bootstrap_id"] != create_events[0]["bootstrap_id"]
        assert not command_events
    finally:
        service.stop()


def test_bootstrap_timeout_clears_pending_without_executing() -> None:
    bus = EventBus()
    service = WorkspaceBootstrapService(bus, timeout_s=0.05)
    command_events: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    bus.subscribe(UI_COMMAND, lambda e: command_events.append(dict(e.payload)))
    bus.subscribe(APP_ERROR, lambda e: errors.append(dict(e.payload)))
    service.start()
    try:
        bus.publish(
            UI_WORKSPACE_REQUIRED,
            {"request_id": "req-5", "text": "note this down"},
            source="test",
        )
        deadline = time.time() + 3.0
        while service.bootstrap_inflight and time.time() < deadline:
            time.sleep(0.01)

        assert not service.bootstrap_inflight
        assert service.pending_command_count == 0
        assert not command_events
        assert errors and "timed out" in str(errors[-1]["message"])
    finally:
        service.stop()


def test_unrelated_workspace_activation_does_not_replay_stale_commands() -> None:
    bus = EventBus()
    service = WorkspaceBootstrapService(bus, timeout_s=0.0)
    create_events: list[dict[str, object]] = []
    command_events: list[dict[str, object]] = []
    bus.subscribe(UI_CREATE_WORKSPACE, lambda e: create_events.append(dict(e.payload)))
    bus.subscribe(UI_COMMAND, lambda e: command_events.append(dict(e.payload)))
    service.start()
    try:
        bus.publish(
            UI_WORKSPACE_REQUIRED,
            {"request_id": "req-6", "text": "note this down"},
            source="test",
        )
        assert len(create_events) == 1

        # A workspace the user opened later — not the one this bootstrap asked
        # for — must not authorize replay into a different context.
        bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-other"}, source="test")
        assert not command_events

        # Nor does a create result belonging to a different bootstrap attempt.
        bus.publish(
            WORKSPACE_CREATE_RESULT,
            {
                "request_id": "rq-9",
                "workspace_id": "ws-other",
                "bootstrap_id": "some-other-bootstrap",
            },
            source="test",
        )
        assert not command_events
    finally:
        service.stop()


def test_pending_queue_is_bounded() -> None:
    bus = EventBus()
    service = WorkspaceBootstrapService(bus, timeout_s=0.0)
    service.start()
    try:
        for index in range(30):
            bus.publish(
                UI_WORKSPACE_REQUIRED,
                {"request_id": f"req-{index}", "text": f"command {index}"},
                source="test",
            )
        assert service.pending_command_count <= 8
    finally:
        service.stop()
