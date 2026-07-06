"""Settings schema and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ai_command_center.domain.capability_provider_settings import (
    DEFAULT_CAPABILITY_PROVIDER_MAP,
    get_capability_provider_choices,
    settings_key_for_kind,
)
from ai_command_center.platform.model_registry import DEFAULT_MODEL_TIER_MAP


@dataclass(frozen=True, slots=True)
class SettingsField:
    name: str
    value_type: type[Any]
    default: Any
    choices: tuple[Any, ...] = ()


class SettingsSchema:
    """Canonical schema for all persisted settings."""

    def __init__(self) -> None:
        self.fields = {
            "model_name": SettingsField("model_name", str, "llama3.2:3b"),
            "provider": SettingsField("provider", str, "ollama", ("ollama", "openai")),
            "openai_base_url": SettingsField(
                "openai_base_url", str, "https://api.openai.com/v1"
            ),
            "openai_api_key": SettingsField("openai_api_key", str, ""),
            "vault_path": SettingsField("vault_path", Path, Path("")),
            "obsidian_vault_path": SettingsField("obsidian_vault_path", str, ""),
            "theme": SettingsField("theme", str, "dark"),
            "accent": SettingsField("accent", str, "#3B82F6"),
            "default_model": SettingsField("default_model", str, "llama3.2:3b"),
            "summarize_model": SettingsField("summarize_model", str, "llama3.2:3b"),
            "model_tier_map": SettingsField(
                "model_tier_map", dict, dict(DEFAULT_MODEL_TIER_MAP)
            ),
            "ollama_url": SettingsField("ollama_url", str, "http://localhost:11434"),
            "ollama_keep_alive": SettingsField("ollama_keep_alive", str, "10m"),
            "hotkey": SettingsField("hotkey", str, "alt+space"),
            "overlay_hotkey": SettingsField("overlay_hotkey", str, "alt+space"),
            "low_memory_mode": SettingsField("low_memory_mode", bool, False),
            "telemetry_enabled": SettingsField("telemetry_enabled", bool, True),
            "otel_enabled": SettingsField("otel_enabled", bool, False),
            "otel_endpoint": SettingsField(
                "otel_endpoint", str, "http://127.0.0.1:4318"
            ),
            "window_width": SettingsField("window_width", int, 1100),
            "window_height": SettingsField("window_height", int, 700),
            "window_alpha": SettingsField("window_alpha", float, 0.95),
            "overlay_mode": SettingsField("overlay_mode", str, "palette"),
            "schema_version": SettingsField("schema_version", int, 1),
            "qwenpaw_enabled": SettingsField("qwenpaw_enabled", bool, False),
            "qwenpaw_url": SettingsField("qwenpaw_url", str, "http://127.0.0.1:8088"),
            "qwenpaw_agent_id": SettingsField("qwenpaw_agent_id", str, "default"),
            "qwenpaw_auto_start": SettingsField("qwenpaw_auto_start", bool, False),
            "qwenpaw_python": SettingsField("qwenpaw_python", str, ""),
            "qwenpaw_auth_token": SettingsField("qwenpaw_auth_token", str, ""),
            "mcp_servers": SettingsField("mcp_servers", dict, {}),
        }
        for kind, default in DEFAULT_CAPABILITY_PROVIDER_MAP.items():
            self.fields[settings_key_for_kind(kind)] = SettingsField(
                settings_key_for_kind(kind),
                str,
                default,
                get_capability_provider_choices(),
            )

    def _coerce(self, field: SettingsField, value: Any) -> Any:
        """Coerce and validate a value against the field type."""
        if field.value_type is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in {"true", "1", "yes"}
            return bool(value)
        if field.value_type is int:
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise TypeError(f"{field.name} must be an int") from exc
        if field.value_type is float:
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise TypeError(f"{field.name} must be a float") from exc
        if field.value_type is str:
            if not isinstance(value, str):
                raise TypeError(f"{field.name} must be a str")
            return value
        if field.value_type is Path:
            return Path(value) if not isinstance(value, Path) else value
        if field.value_type is dict:
            if isinstance(value, dict):
                return value
            return {}
        if issubclass(field.value_type, Enum):
            if isinstance(value, field.value_type):
                return value
            return field.value_type(value)
        return value

    def validate(self, key: str, value: Any) -> Any:
        field = self.fields[key]
        validated = self._coerce(field, value)
        choices = field.choices
        if key.startswith("capability_provider_"):
            choices = get_capability_provider_choices()
        if choices and validated not in choices:
            raise ValueError(f"{key} must be one of {choices}")
        return validated
