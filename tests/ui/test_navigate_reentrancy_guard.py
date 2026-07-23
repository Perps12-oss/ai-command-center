"""Hard navigate reentrancy / same-view guards (post-#106 freeze after 2 clicks)."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_NAVIGATE
from ai_command_center.ui.shell.event_coordinator import EventCoordinatorMixin
from ai_command_center.ui.shell.view_manager import ViewManagerMixin


class _SyncUIQueue:
    def enqueue(self, callback) -> None:
        callback()


class _GuardShell(ViewManagerMixin, EventCoordinatorMixin):
    """Exercises production _navigate guard without building CTk widgets."""

    def __init__(self) -> None:
        self._bus = EventBus()
        self._bus_unsubs: list = []
        self._ui_queue = _SyncUIQueue()
        self._views = {"chat": object(), "memory": object()}
        self._current_view = "chat"
        self._workspace_os_enabled = False
        self._default_view = "chat"
        self.show_calls: list[str] = []
        self.publish_calls: list[str] = []
        self._controller = type(
            "C",
            (),
            {
                "publish_clear_chat_entity": lambda self: None,
                "publish_navigate": lambda self, view_id: self._owner.publish_calls.append(
                    view_id
                ),
                "snapshot": lambda self: type("S", (), {"active_workspace_id": ""})(),
            },
        )()
        self._controller._owner = self
        self._wire_navigation_events()

    def _policy_resolve_view(self, view_id: str) -> str:
        return view_id

    def _show_view(self, view_id: str) -> None:
        self.show_calls.append(view_id)
        self._current_view = view_id
        # Simulate a buggy bus echo that used to re-enter _navigate.
        self._bus.publish(UI_NAVIGATE, {"view": view_id}, source="ui")


def test_same_view_navigate_is_noop() -> None:
    shell = _GuardShell()
    shell._navigate("chat")
    assert shell.show_calls == []
    assert shell.publish_calls == []


def test_navigate_publishes_once_even_if_bus_echoes() -> None:
    shell = _GuardShell()
    shell._navigate("memory")
    assert shell.show_calls == ["memory"]
    assert shell.publish_calls == ["memory"]
    # Echo with source=ui must not re-enter.
    assert shell.show_calls == ["memory"]


def test_reentrant_navigate_is_ignored() -> None:
    shell = _GuardShell()
    shell._navigate_reentrant = True
    shell._navigate("memory")
    assert shell.show_calls == []
    assert shell.publish_calls == []


def test_external_same_view_does_not_show_again() -> None:
    shell = _GuardShell()
    shell._bus.publish(UI_NAVIGATE, {"view": "chat"}, source="state_capability_tools")
    assert shell.show_calls == []
