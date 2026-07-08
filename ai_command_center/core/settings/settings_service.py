"""Settings service placeholder for the architecture enforcement spec."""

from __future__ import annotations

import json
from typing import Any

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import SETTINGS_SNAPSHOT, SETTINGS_UPDATED
from ai_command_center.core.settings.migration_manager import MigrationManager
from ai_command_center.core.settings.settings_repository import SettingsRepository
from ai_command_center.core.settings.settings_schema import SettingsSchema
from ai_command_center.domain.settings_snapshot import SettingsSnapshot


def _model_tier_map_from_payload(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items() if str(k).strip() and str(v).strip()}
    if isinstance(value, str):
        try:
            parsed = json.loads(value or "{}")
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return {
                str(k): str(v)
                for k, v in parsed.items()
                if str(k).strip() and str(v).strip()
            }
    return {}


class SettingsService:
    """Minimal service facade around a settings repository and schema."""

    def __init__(
        self,
        repo: SettingsRepository,
        schema: SettingsSchema | None = None,
        *,
        bus: EventBus | None = None,
    ) -> None:
        self._repo = repo
        self._schema = schema or SettingsSchema()
        self._bus = bus
        self._migration = MigrationManager()

    def get_snapshot(self) -> SettingsSnapshot:
        payload = self._migration.migrate(self._repo.get_all())
        return SettingsSnapshot(
            theme=str(payload.get("theme", "dark")),
            accent=str(payload.get("accent", "#3B82F6")),
            default_model=str(payload.get("default_model", "llama3.2:3b")),
            summarize_model=str(payload.get("summarize_model", "llama3.2:3b")),
            ollama_url=str(payload.get("ollama_url", "http://localhost:11434")),
            hotkey=str(payload.get("hotkey", "alt+space")),
            low_memory_mode=bool(payload.get("low_memory_mode", False)),
            window_width=int(payload.get("window_width", 1100)),
            window_height=int(payload.get("window_height", 700)),
            window_alpha=float(payload.get("window_alpha", 0.95)),
            obsidian_vault_path=str(payload.get("obsidian_vault_path", "")),
            overlay_mode=str(payload.get("overlay_mode", "palette")),
            model_name=str(payload.get("model_name", "llama3.2:3b")),
            provider=str(payload.get("provider", "ollama")),
            openai_base_url=str(
                payload.get("openai_base_url", "https://api.openai.com/v1")
            ),
            openai_api_key=str(payload.get("openai_api_key", "")),
            vault_path=payload.get("vault_path", ""),
            overlay_hotkey=str(payload.get("overlay_hotkey", "alt+space")),
            telemetry_enabled=bool(payload.get("telemetry_enabled", True)),
            model_tier_map=_model_tier_map_from_payload(payload.get("model_tier_map", {})),
            schema_version=int(payload.get("schema_version", 1)),
        )

    def set(self, key: str, value: Any) -> None:
        validated = value
        if key in self._schema.fields:
            try:
                validated = self._schema.validate(key, value)
            except (TypeError, ValueError):
                validated = self._schema.fields[key].default
        if isinstance(validated, dict):
            validated = json.dumps(validated, sort_keys=True, separators=(",", ":"))
        self._repo.set(key, validated)
        if self._bus is not None:
            self._bus.publish(SETTINGS_UPDATED, {"key": key, "value": validated}, source="settings")
            self._bus.publish(SETTINGS_SNAPSHOT, self.get_snapshot().to_payload(), source="settings")

    def update(self, **values: Any) -> None:
        for key, value in values.items():
            self.set(key, value)

