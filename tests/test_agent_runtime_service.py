"""Agent runtime service tests (A1 skeleton)."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_SPAWN_REQUEST,
    AGENT_TERMINATED,
    UI_COMMAND,
)
from ai_command_center.services.agent_runtime_service import AgentRuntimeService


def test_agent_spawn_publishes_lifecycle_and_ui_command() -> None:
    bus = EventBus()
    service = AgentRuntimeService(bus)
    spawned: list[dict] = []
    commands: list[dict] = []
    terminated: list[dict] = []

    bus.subscribe(AGENT_SPAWNED, lambda e: spawned.append(dict(e.payload)))
    bus.subscribe(UI_COMMAND, lambda e: commands.append(dict(e.payload)))
    bus.subscribe(AGENT_TERMINATED, lambda e: terminated.append(dict(e.payload)))

    service.start()
    bus.publish(
        AGENT_SPAWN_REQUEST,
        {"task": "hello agent", "request_id": "req-1"},
        source="test",
    )
    service.stop()

    assert spawned
    assert spawned[0]["request_id"] == "req-1"
    assert commands
    assert commands[0]["text"] == "hello agent"
    assert not terminated  # terminates on chat.complete in production path
