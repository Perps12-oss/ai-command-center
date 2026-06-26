"""Settings schema and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


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
            "vault_path": SettingsField("vault_path", Path, Path("")),
            "obsidian_vault_path": SettingsField("obsidian_vault_path", str, ""),
            "theme": SettingsField("theme", str, "dark"),
            "accent": SettingsField("accent", str, "#3B82F6"),
            "default_model": SettingsField("default_model", str, "llama3.2:3b"),
            "summarize_model": SettingsField("summarize_model", str, "llama3.2:3b"),
            "ollama_url": SettingsField("ollama_url", str, "http://localhost:11434"),
            "ollama_keep_alive": SettingsField("ollama_keep_alive", str, "10m"),
            "hotkey": SettingsField("hotkey", str, "alt+space"),
            "overlay_hotkey": SettingsField("overlay_hotkey", str, "alt+space"),
            "low_memory_mode": SettingsField("low_memory_mode", bool, False),
            "telemetry_enabled": SettingsField("telemetry_enabled", bool, True),
            "window_width": SettingsField("window_width", int, 1100),
            "window_height": SettingsField("window_height", int, 700),
            "window_alpha": SettingsField("window_alpha", float, 0.95),
            "overlay_mode": SettingsField("overlay_mode", str, "palette"),
            "schema_version": SettingsField("schema_version", int, 1),
        }

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
        if issubclass(field.value_type, Enum):
            if isinstance(value, field.value_type):
                return value
            return field.value_type(value)
        return value

    def validate(self, key: str, value: Any) -> Any:
        field = self.fields[key]
        validated = self._coerce(field, value)
        if field.choices and validated not in field.choices:
            raise ValueError(f"{key} must be one of {field.choices}")
        return validated
