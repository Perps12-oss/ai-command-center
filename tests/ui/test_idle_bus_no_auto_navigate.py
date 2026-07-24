"""Idle bus traffic must not force sidebar navigation."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    MEMORY_SELECTED,
    NOTE_SEARCH_RESULTS,
    PLUGIN_CATALOG,
)
from ai_command_center.ui.shell.event_coordinator import EventCoordinatorMixin


class _SyncUIQueue:
    def __init__(self) -> None:
        self.calls: list = []

    def enqueue(self, callback) -> None:
        self.calls.append(callback)
        callback()


class _Shell(EventCoordinatorMixin):
    def __init__(self) -> None:
        self._bus = EventBus()
        self._bus_unsubs: list = []
        self._ui_queue = _SyncUIQueue()
        self._current_view = "command_center"
        self.navigate_calls: list[str] = []
        self.refresh_calls = 0
        self.toast_calls: list[str] = []
        self._toast = type(
            "T",
            (),
            {"show": lambda self, msg, kind="info", action=None: self._owner.toast_calls.append(msg)},
        )()
        self._toast._owner = self
        self._wire_note_events()
        self._wire_memory_events()
        self._wire_plugin_events()

    def _navigate(self, view_id: str, *, clear_chat_entity: bool = False) -> None:
        self.navigate_calls.append(view_id)

    def _queue_state_refresh(self) -> None:
        self.refresh_calls += 1

    def _notes_view(self):
        return None

    def _memory_view(self):
        return None


def test_plugin_catalog_does_not_navigate() -> None:
    shell = _Shell()
    shell._bus.publish(PLUGIN_CATALOG, {"plugins": []}, source="plugin_registry")
    assert shell.navigate_calls == []
    assert shell.refresh_calls >= 1


def test_note_search_results_do_not_navigate() -> None:
    shell = _Shell()
    shell._bus.publish(
        NOTE_SEARCH_RESULTS,
        {"results": [], "query": "x"},
        source="obsidian",
    )
    assert shell.navigate_calls == []
    assert shell.refresh_calls >= 1


def test_memory_selected_does_not_navigate() -> None:
    shell = _Shell()
    shell._bus.publish(MEMORY_SELECTED, {"label": "x"}, source="memory")
    assert shell.navigate_calls == []
    assert any("Memory:" in t for t in shell.toast_calls)
