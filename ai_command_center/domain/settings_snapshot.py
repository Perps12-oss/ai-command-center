"""Canonical settings snapshot contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    """Canonical runtime settings payload used by the app state and services."""

    theme: str = "dark"
    accent: str = "#3B82F6"
    default_model: str = "llama3.2:3b"
    summarize_model: str = "llama3.2:3b"
    ollama_url: str = "http://localhost:11434"
    hotkey: str = "alt+space"
    low_memory_mode: bool = False
    window_width: int = 1100
    window_height: int = 700
    window_alpha: float = 0.95
    obsidian_vault_path: str = ""
    overlay_mode: str = "palette"

    # Additional fields used by the architecture enforcement spec.
    model_name: str = "llama3.2:3b"
    provider: str = "ollama"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    vault_path: str | Path = ""
    overlay_hotkey: str = "alt+space"
    telemetry_enabled: bool = True
    model_tier_map: dict[str, str] | None = None
    schema_version: int = 1

    def to_payload(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "accent": self.accent,
            "default_model": self.default_model,
            "summarize_model": self.summarize_model,
            "ollama_url": self.ollama_url,
            "hotkey": self.hotkey,
            "low_memory_mode": self.low_memory_mode,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_alpha": self.window_alpha,
            "obsidian_vault_path": self.obsidian_vault_path,
            "overlay_mode": self.overlay_mode,
            "model_name": self.model_name,
            "provider": self.provider,
            "openai_base_url": self.openai_base_url,
            "openai_api_key": self.openai_api_key,
            "vault_path": str(self.vault_path),
            "overlay_hotkey": self.overlay_hotkey,
            "telemetry_enabled": self.telemetry_enabled,
            "model_tier_map": dict(self.model_tier_map or {}),
            "schema_version": self.schema_version,
        }
