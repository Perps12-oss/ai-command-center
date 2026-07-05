"""Settings persistence via SQLite (Phase 1 — no UI)."""

from __future__ import annotations

from typing import Any, Callable

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    SETTINGS_CHANGED,
    SETTINGS_SET_REQUEST,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.core.settings.settings_service import SettingsService as CoreSettingsService
from ai_command_center.domain.settings_snapshot import SettingsSnapshot
from ai_command_center.platform.secret_store import store_openai_api_key
from ai_command_center.providers.defaults import default_model_for_provider
from ai_command_center.repositories.settings_repository import SettingsRepository
from ai_command_center.services.base import BaseService

_DEFAULTS: dict[str, str] = {
    "theme": "dark",
    "accent": "#3B82F6",
    "ollama_url": "http://localhost:11434",
    "ollama_keep_alive": "10m",
    "default_model": "llama3.2:3b",
    "summarize_model": "llama3.2:3b",
    "hotkey": "alt+space",
    "low_memory_mode": "false",
    "window_width": "1100",
    "window_height": "700",
    "window_alpha": "0.95",
    "obsidian_vault_path": "",
    "overlay_mode": "palette",
    "provider": "ollama",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_api_key": "",
    "qwenpaw_enabled": "false",
    "qwenpaw_url": "http://127.0.0.1:8088",
    "qwenpaw_agent_id": "default",
    "qwenpaw_auto_start": "false",
    "qwenpaw_python": "",
    "qwenpaw_auth_token": "",
}


class SettingsService(BaseService):
    """Bus-facing settings service: validates writes and publishes SettingsSnapshot."""

    name = "settings"

    def __init__(self, bus: EventBus, repo: SettingsRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._unsubscribers: list[Callable[[], None]] = []
        self._core_settings = CoreSettingsService(repo=repo, bus=bus)

    def _on_load(self) -> None:
        self._repo.ensure_defaults(_DEFAULTS)
        self._unsubscribers.append(
            self._bus.subscribe(SETTINGS_SET_REQUEST, self._on_set_request)
        )
        self._publish_snapshot()

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_set_request(self, event: Event) -> None:
        key = event.payload.get("key")
        value = event.payload.get("value")
        if key is None or value is None:
            return
        self.set(str(key), value)

    def set(self, key: str, value: Any) -> None:
        if key == "openai_api_key":
            value = store_openai_api_key(str(value))
        if key == "provider":
            provider = str(value).strip() or "ollama"
            model = default_model_for_provider(provider)
            self._core_settings.set("provider", provider)
            self._core_settings.set("default_model", model)
            self._core_settings.set("summarize_model", model)
        else:
            self._core_settings.set(key, value)
        self._bus.publish(
            SETTINGS_CHANGED,
            {"key": key, "value": value},
            source=self.name,
        )
        self._publish_snapshot()

    def get_snapshot(self) -> SettingsSnapshot:
        return self._core_settings.get_snapshot()

    def _publish_snapshot(self) -> None:
        self._bus.publish(
            SETTINGS_SNAPSHOT,
            self._core_settings.get_snapshot().to_payload(),
            source=self.name,
        )
