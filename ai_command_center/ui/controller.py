"""UI bridge — EventBus and AppState only (no ApplicationCore)."""

from __future__ import annotations

from collections.abc import Callable

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus


class UIController:
    """
    Mediates UI intents → EventBus.
    UI reads AppState via snapshot + subscribe callbacks.
    """

    def __init__(
        self,
        bus: EventBus,
        state_store: AppStateStore,
        on_state: Callable[[], None],
    ) -> None:
        self._bus = bus
        self._state_store = state_store
        self._state_store.subscribe(lambda _s: on_state())

    def snapshot(self):
        return self._state_store.snapshot

    def publish_command(self, text: str, *, clipboard: str | None = None) -> None:
        payload: dict[str, str] = {"text": text}
        if clipboard:
            payload["clipboard"] = clipboard
        self._bus.publish(
            "ui.command",
            payload,
            source="ui",
        )

    def publish_navigate(self, view_id: str) -> None:
        self._bus.publish(
            "ui.navigate",
            {"view": view_id},
            source="ui",
        )

    def publish_palette_open(self) -> None:
        self._bus.publish("ui.palette_open", {}, source="ui")

    def publish_palette_close(self) -> None:
        self._bus.publish("ui.palette_close", {}, source="ui")

    def request_settings_change(self, key: str, value: str) -> None:
        self._bus.publish(
            "settings.set_request",
            {"key": key, "value": value},
            source="ui",
        )

    def publish_chat_cancel(self, request_id: str) -> None:
        self._bus.publish(
            "ui.chat_cancel",
            {"request_id": request_id},
            source="ui",
        )

    def publish_note_select(self, path: str) -> None:
        self._bus.publish(
            "note.select",
            {"path": path},
            source="ui",
        )
