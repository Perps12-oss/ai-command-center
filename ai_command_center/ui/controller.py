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
    MEMORY_REMEMBER,
    NOTE_SELECT,
    OVERLAY_ANCHOR,
    OVERLAY_HIDE,
    OVERLAY_SHOW,
    PERMISSION_CHECK_RESULT,
    PLUGIN_DISABLE_REQUEST,
    PLUGIN_ENABLE_REQUEST,
    SETTINGS_SET_REQUEST,
    UI_CHAT_CANCEL,
    UI_CHAT_NEW_SESSION,
    UI_COMMAND,
    UI_LAUNCH_RESOURCE,
    UI_NAVIGATE,
    UI_OPEN_CHAT,
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
        self._on_state = on_state
        self._unsub_state: Callable[[], None] | None = None
        self._unsub_state = self._state_store.subscribe(lambda _s: on_state())

    def close(self) -> None:
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None

    def snapshot(self):
        return self._state_store.snapshot

    def publish_command(
        self,
        text: str,
        *,
        clipboard: str | None = None,
        workspace_entity: dict[str, str] | None = None,
    ) -> None:
        payload: dict[str, str] = {"text": text}
        if clipboard:
            payload["clipboard"] = clipboard
        if workspace_entity:
            entity_id = str(workspace_entity.get("entity_id", "")).strip()
            if entity_id:
                payload["workspace_entity_id"] = entity_id
                payload["workspace_entity_type"] = str(
                    workspace_entity.get("entity_type", "")
                )
                payload["workspace_entity_title"] = str(
                    workspace_entity.get("entity_title", "")
                )
                description = str(workspace_entity.get("description", "")).strip()
                url = str(workspace_entity.get("url", "")).strip()
                path = str(workspace_entity.get("path", "")).strip()
                if description:
                    payload["workspace_entity_description"] = description
                if url:
                    payload["workspace_entity_url"] = url
                if path:
                    payload["workspace_entity_path"] = path
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

    def publish_memory_remember(self, label: str, content: str) -> None:
        self._bus.publish(
            MEMORY_REMEMBER,
            {"label": label, "content": content},
            source="ui",
        )

    def publish_launch_resource(self, payload: dict[str, object]) -> None:
        self._bus.publish(UI_LAUNCH_RESOURCE, payload, source="ui")

    def publish_open_chat(
        self,
        entity_id: str,
        entity_type: str,
        title: str,
        *,
        description: str = "",
        url: str = "",
        path: str = "",
    ) -> None:
        payload: dict[str, str] = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "title": title,
        }
        if description:
            payload["description"] = description
        if url:
            payload["url"] = url
        if path:
            payload["path"] = path
        self._bus.publish(UI_OPEN_CHAT, payload, source="ui")

    def publish_clear_chat_entity(self) -> None:
        """Detach workspace entity context (generic chat navigation)."""
        self._bus.publish(UI_OPEN_CHAT, {"entity_id": ""}, source="ui")

    def publish_chat_new_session(self) -> None:
        """Start a fresh generic chat session and clear entity attach."""
        self._bus.publish(UI_CHAT_NEW_SESSION, {}, source="ui")

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

    def publish_permission_result(
        self,
        *,
        check_id: str,
        granted: bool,
        permissions: list[str] | tuple[str, ...],
        actor_type: str = "agent",
        actor_id: str = "",
    ) -> None:
        """Publish user approval/denial for interactive permission checks."""
        self._bus.publish(
            PERMISSION_CHECK_RESULT,
            {
                "check_id": check_id,
                "granted": granted,
                "permissions": list(permissions),
                "actor_type": actor_type,
                "actor_id": actor_id,
            },
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
