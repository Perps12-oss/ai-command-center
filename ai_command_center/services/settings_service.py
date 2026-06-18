"""Settings persistence via SQLite (Phase 1 — no UI)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.db.repository import SettingsRepository
from ai_command_center.services.base import BaseService

_DEFAULTS: dict[str, str] = {
    "theme": "dark",
    "accent": "#3B82F6",
    "ollama_url": "http://localhost:11434",
    "ollama_keep_alive": "10m",
    "default_model": "llama3.2:3b",
    "hotkey": "alt+space",
    "low_memory_mode": "false",
    "window_width": "1100",
    "window_height": "700",
    "obsidian_vault_path": "",
}


class SettingsService(BaseService):
    name = "settings"

    def __init__(self, bus: EventBus, repo: SettingsRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._repo.ensure_defaults(_DEFAULTS)
        self._unsubscribers.append(
            self._bus.subscribe("settings.set_request", self._on_set_request)
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
        self.set(str(key), str(value))

    def set(self, key: str, value: str) -> None:
        self._repo.set(key, value)
        self._bus.publish(
            "settings.changed",
            {"key": key, "value": value},
            source=self.name,
        )
        self._publish_snapshot()

    def _publish_snapshot(self) -> None:
        payload = {k: self._repo.get(k, v) for k, v in _DEFAULTS.items()}
        self._bus.publish("settings.snapshot", payload, source=self.name)
