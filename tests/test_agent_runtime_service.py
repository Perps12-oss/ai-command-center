"""Agent runtime service tests (A1 skeleton + Track 7 permission gate)."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_SPAWN_REQUEST,
    AGENT_TERMINATED,
    PERMISSION_CHECK_REQUEST,
    UI_COMMAND,
)
from ai_command_center.core.permission.permission_service import PermissionService
from ai_command_center.services.agent_runtime_service import AgentRuntimeService


def test_agent_spawn_publishes_lifecycle_and_ui_command() -> None:
    bus = EventBus()
    permission = PermissionService(bus)
    permission.wire_bus_handlers()

    def approve(event) -> None:
        if event.payload.get("interactive"):
            from ai_command_center.core.events.topics import PERMISSION_CHECK_RESULT

            bus.publish(
                PERMISSION_CHECK_RESULT,
                {
                    "check_id": event.payload["check_id"],
                    "granted": True,
                    "permissions": list(event.payload.get("permissions") or []),
                    "actor_type": "agent",
                    "actor_id": event.payload.get("actor_id"),
                },
                source="ui",
            )

    bus.subscribe(PERMISSION_CHECK_REQUEST, approve)

    service = AgentRuntimeService(bus)
    spawned: list[dict] = []
    commands: list[dict] = []
    terminated: list[dict] = []
    checks: list[dict] = []

    bus.subscribe(AGENT_SPAWNED, lambda e: spawned.append(dict(e.payload)))
    bus.subscribe(UI_COMMAND, lambda e: commands.append(dict(e.payload)))
    bus.subscribe(AGENT_TERMINATED, lambda e: terminated.append(dict(e.payload)))
    bus.subscribe(PERMISSION_CHECK_REQUEST, lambda e: checks.append(dict(e.payload)))

    service.start()
    bus.publish(
        AGENT_SPAWN_REQUEST,
        {"task": "hello agent", "request_id": "req-1"},
        source="test",
    )
    service.stop()

    assert checks
    assert spawned
    assert spawned[0]["request_id"] == "req-1"
    assert commands
    assert commands[0]["text"] == "hello agent"
    assert not terminated  # terminates on chat.complete in production path
