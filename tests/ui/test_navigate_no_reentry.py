"""Regression: UI_NAVIGATE must not re-enter ViewManager._navigate.

Before the fix, sidebar/palette navigation published UI_NAVIGATE and the shell
handler called _navigate again, which republished — an infinite UIQueue loop
that froze the app after launch/page navigation.
"""

from __future__ import annotations

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import UI_NAVIGATE
from ai_command_center.ui.shell.event_coordinator import EventCoordinatorMixin
from ai_command_center.ui.shell.view_manager import VIEW_IDS


class _SyncUIQueue:
    def __init__(self) -> None:
        self.calls: list = []

    def enqueue(self, callback) -> None:
        self.calls.append(callback)
        callback()


class _NavigateShell(EventCoordinatorMixin):
    """Minimal shell surface for EventCoordinatorMixin navigate wiring."""

    def __init__(self) -> None:
        self._bus = EventBus()
        self._bus_unsubs: list = []
        self._ui_queue = _SyncUIQueue()
        self._controller = type(
            "C",
            (),
            {"publish_clear_chat_entity": lambda self: setattr(self, "cleared", True)},
        )()
        self.navigate_calls: list[tuple[str, bool]] = []
        self.show_view_calls: list[str] = []
        self._wire_navigation_events()

    def _navigate(self, view_id: str, *, clear_chat_entity: bool = False) -> None:
        self.navigate_calls.append((view_id, clear_chat_entity))
        # Mirror production: local navigate publishes UI_NAVIGATE for telemetry.
        self._bus.publish(UI_NAVIGATE, {"view": view_id}, source="ui")

    def _show_view(self, view_id: str) -> None:
        self.show_view_calls.append(view_id)


def test_ui_sourced_navigate_does_not_reenter_navigate() -> None:
    shell = _NavigateShell()
    shell._navigate("chat")
    assert shell.navigate_calls == [("chat", False)]
    assert shell.show_view_calls == []


def test_external_navigate_applies_show_view_without_republish() -> None:
    shell = _NavigateShell()
    shell._bus.publish(
        UI_NAVIGATE,
        {"view": "memory"},
        source="state_capability_tools",
    )
    assert shell.show_view_calls == ["memory"]
    assert shell.navigate_calls == []


def test_external_navigate_unknown_view_falls_back_to_command_center() -> None:
    shell = _NavigateShell()
    shell._bus.publish(UI_NAVIGATE, {"view": "not-a-view"}, source="tools")
    assert shell.show_view_calls == ["command_center"]
    assert "command_center" in VIEW_IDS


def test_ui_navigate_event_object_source_ui_is_ignored() -> None:
    shell = _NavigateShell()
    shell._on_ui_navigate(
        Event(topic=UI_NAVIGATE, payload={"view": "settings"}, source="ui")
    )
    assert shell.navigate_calls == []
    assert shell.show_view_calls == []
