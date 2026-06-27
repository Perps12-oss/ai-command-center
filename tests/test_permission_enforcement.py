"""Tests for action-level permission enforcement and timeline recording."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_command_center.core.action.action_registry import ActionRegistry
from ai_command_center.core.event_bus import EVENT_TIMELINE_EVENT, EventBus
from ai_command_center.core.permission.permission import Permission
from ai_command_center.core.permission.permission_service import PermissionService
from ai_command_center.core.timeline.timeline_repository import TimelineRepository
from ai_command_center.core.timeline.timeline_service import TimelineService
from ai_command_center.db.connection import connect, init_database


@pytest.fixture
def registry_with_timeline():
    db = init_database(connect(Path(":memory:")))
    bus = EventBus()
    timeline_repo = TimelineRepository(db)
    timeline_service = TimelineService(timeline_repo, bus)
    permission_service = PermissionService(bus)
    permission_service.start()
    registry = ActionRegistry(bus)
    timeline_service.start()
    yield bus, registry, timeline_service
    timeline_service.stop()
    permission_service.stop()
    registry._permission_client.close()


def test_user_can_invoke_action_with_required_permission(registry_with_timeline):
    bus, registry, _ = registry_with_timeline

    invoked = []

    def handler(params):
        invoked.append(params)
        return {"ok": True}

    action = registry.register(
        action_type="launch",
        name="Open Folder",
        handler=handler,
        required_permissions=[Permission.EXECUTE_ACTION.value],
    )

    result = registry.invoke(action.id)
    assert result == {"ok": True}
    assert len(invoked) == 1


def test_agent_denied_and_records_timeline_event(registry_with_timeline):
    bus, registry, timeline_service = registry_with_timeline

    def handler(params):
        return {"ok": True}

    action = registry.register(
        action_type="launch",
        name="Execute Command",
        handler=handler,
        required_permissions=[Permission.LAUNCH_TOOL.value],
    )

    timeline_events = []
    bus.subscribe(EVENT_TIMELINE_EVENT, timeline_events.append)

    with pytest.raises(PermissionError):
        registry.invoke(action.id, actor_type="agent")

    # The action registry should have published a Permission Denied timeline event.
    action_registry_events = [
        e for e in timeline_events
        if e.source == "action_registry" and e.payload.get("event_type") == "Permission Denied"
    ]
    assert len(action_registry_events) >= 1
    payload = action_registry_events[0].payload
    assert payload["payload"]["denied_permissions"] == [Permission.LAUNCH_TOOL.value]

    # The handler should never have run, and the event should be persisted.
    recent = timeline_service.get_recent(10)
    assert any(e.event_type == "Permission Denied" for e in recent)


def test_invoke_ai_allows_ai_executable_actions(registry_with_timeline):
    bus, registry, _ = registry_with_timeline

    def handler(params):
        return {"ok": True}

    action = registry.register(
        action_type="launch",
        name="AI Tool",
        handler=handler,
        ai_executable=True,
        required_permissions=[Permission.USE_AI.value],
    )

    result = registry.invoke_ai(action.id)
    assert result == {"ok": True}


def test_invoke_ai_rejects_non_ai_executable_actions(registry_with_timeline):
    bus, registry, _ = registry_with_timeline

    def handler(params):
        return {"ok": True}

    action = registry.register(
        action_type="launch",
        name="User Only",
        handler=handler,
        ai_executable=False,
    )

    with pytest.raises(PermissionError, match="not AI-executable"):
        registry.invoke_ai(action.id)
