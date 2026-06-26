"""UI bridge — EventBus and AppState only (no ApplicationCore)."""

from __future__ import annotations

from collections.abc import Callable

import pyperclip

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_EXPORT_REQUEST,
    CLIPBOARD_CONTENT,
    CLIPBOARD_REQUEST,
    MEMORY_DELETE_REQUEST,
    NOTE_SELECT,
    OVERLAY_ANCHOR,
    OVERLAY_HIDE,
    OVERLAY_SHOW,
    PLUGIN_DISABLE_REQUEST,
    PLUGIN_ENABLE_REQUEST,
    SETTINGS_SET_REQUEST,
    UI_CHAT_CANCEL,
    UI_COMMAND,
    UI_NAVIGATE,
    UI_PALETTE_CLOSE,
    UI_PALETTE_OPEN,
)


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
            UI_COMMAND,
            payload,
            source="ui",
        )

    def publish_navigate(self, view_id: str) -> None:
        self._bus.publish(
            UI_NAVIGATE,
            {"view": view_id},
            source="ui",
        )

    def publish_palette_open(self) -> None:
        self._bus.publish(UI_PALETTE_OPEN, {}, source="ui")
        self._bus.publish(OVERLAY_SHOW, {"mode": "palette", "x": 0, "y": 0}, source="ui")

    def publish_palette_close(self) -> None:
        self._bus.publish(UI_PALETTE_CLOSE, {}, source="ui")
        self._bus.publish(OVERLAY_HIDE, {}, source="ui")

    def publish_overlay_show(self, *, mode: str = "compact", x: int = 0, y: int = 0) -> None:
        self._bus.publish(
            OVERLAY_SHOW,
            {"mode": mode, "x": x, "y": y},
            source="ui",
        )

    def publish_overlay_anchor(self, x: int, y: int) -> None:
        self._bus.publish(OVERLAY_ANCHOR, {"x": x, "y": y}, source="ui")

    def request_settings_change(self, key: str, value: str) -> None:
        self._bus.publish(
            SETTINGS_SET_REQUEST,
            {"key": key, "value": value},
            source="ui",
        )

    def publish_chat_cancel(self, request_id: str) -> None:
        self._bus.publish(
            UI_CHAT_CANCEL,
            {"request_id": request_id},
            source="ui",
        )

    def publish_note_select(self, path: str) -> None:
        self._bus.publish(
            NOTE_SELECT,
            {"path": path},
            source="ui",
        )

    def publish_plugin_toggle(self, plugin_id: str, enabled: bool) -> None:
        topic = PLUGIN_ENABLE_REQUEST if enabled else PLUGIN_DISABLE_REQUEST
        self._bus.publish(topic, {"id": plugin_id}, source="ui")

    def publish_memory_delete(self, memory_id: str) -> None:
        self._bus.publish(
            MEMORY_DELETE_REQUEST,
            {"id": memory_id},
            source="ui",
        )

    def publish_chat_export(self, history: list[dict]) -> None:
        self._bus.publish(
            CHAT_EXPORT_REQUEST,
            {"history": list(history)},
            source="ui",
        )

    def read_clipboard(self) -> str | None:
        try:
            text = pyperclip.paste()
        except Exception:
            return None
        if not text or not str(text).strip():
            return None
        return str(text)

    def publish_clipboard_request(self) -> None:
        self._bus.publish(CLIPBOARD_REQUEST, {}, source="ui")
        try:
            text = self.read_clipboard()
        except Exception:
            text = None
        if text:
            self._bus.publish(CLIPBOARD_CONTENT, {"text": text}, source="ui")
