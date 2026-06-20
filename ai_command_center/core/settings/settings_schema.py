"""Settings schema and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SettingsField:
    name: str
    value_type: type[Any]
    default: Any
    choices: tuple[Any, ...] = ()


class SettingsSchema:
    """Minimal schema container for future settings normalization."""

    def __init__(self) -> None:
        self.fields = {
            "model_name": SettingsField("model_name", str, "llama3.2:3b"),
            "provider": SettingsField("provider", str, "ollama", ("ollama", "openai")),
            "vault_path": SettingsField("vault_path", Path, Path("")),
            "theme": SettingsField("theme", str, "dark", ("dark", "light")),
            "overlay_hotkey": SettingsField("overlay_hotkey", str, "alt+space"),
            "telemetry_enabled": SettingsField("telemetry_enabled", bool, True),
            "schema_version": SettingsField("schema_version", int, 1),
        }

    def validate(self, key: str, value: Any) -> Any:
        field = self.fields[key]
        if field.value_type is bool and not isinstance(value, bool):
            raise TypeError(f"{key} must be a bool")
        if field.value_type is int and not isinstance(value, int):
            raise TypeError(f"{key} must be an int")
        if field.value_type is float and not isinstance(value, float):
            raise TypeError(f"{key} must be a float")
        if field.value_type is str and not isinstance(value, str):
            raise TypeError(f"{key} must be a str")
        if field.value_type is Path:
            return Path(value) if not isinstance(value, Path) else value
        if field.choices and value not in field.choices:
            raise ValueError(f"{key} must be one of {field.choices}")
        return value
