"""EventBus must hard-drop reentrant UI_NAVIGATE publishes (storm break)."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_NAVIGATE


def test_reentrant_ui_navigate_publish_is_dropped() -> None:
    bus = EventBus()
    seen: list[str] = []

    def handler(event) -> None:
        seen.append(str(event.payload.get("view", "")))
        # Classic feedback loop: handler republishes navigate.
        bus.publish(UI_NAVIGATE, {"view": "memory"}, source="buggy_handler")

    bus.subscribe(UI_NAVIGATE, handler)
    bus.publish(UI_NAVIGATE, {"view": "chat"}, source="ui")

    assert seen == ["chat"]
    assert bus._navigate_dropped_reentrant >= 1


def test_sequential_ui_navigate_still_delivered() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe(UI_NAVIGATE, lambda e: seen.append(str(e.payload.get("view", ""))))
    bus.publish(UI_NAVIGATE, {"view": "chat"}, source="ui")
    bus.publish(UI_NAVIGATE, {"view": "memory"}, source="ui")
    assert seen == ["chat", "memory"]
    assert bus._navigate_dropped_reentrant == 0
