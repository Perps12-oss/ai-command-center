from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_COMMAND,
    UI_CREATE_WORKSPACE,
    UI_WORKSPACE_REQUIRED,
    WORKSPACE_ACTIVE,
)
from ai_command_center.services.workspace_bootstrap_service import WorkspaceBootstrapService


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
        assert not command_events

        bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-1"}, source="test")
        assert len(command_events) == 1
        assert command_events[0]["text"] == "> echo hello"
        assert command_events[0]["replayed_from_workspace_bootstrap"] is True
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
