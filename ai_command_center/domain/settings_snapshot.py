"""Canonical settings snapshot contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_command_center.domain.capability_provider_settings import (
    DEFAULT_CAPABILITY_PROVIDER_MAP,
)


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
    otel_enabled: bool = False
    otel_endpoint: str = "http://127.0.0.1:4318"
    schema_version: int = 5
    capability_provider_map: dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_CAPABILITY_PROVIDER_MAP)
    )
    qwenpaw_enabled: bool = False
    qwenpaw_url: str = "http://127.0.0.1:8088"
    qwenpaw_agent_id: str = "default"
    qwenpaw_auto_start: bool = False
    qwenpaw_python: str = ""
    qwenpaw_auth_token: str = ""
    mcp_servers: dict[str, dict[str, object]] = field(default_factory=dict)

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
            "otel_enabled": self.otel_enabled,
            "otel_endpoint": self.otel_endpoint,
            "schema_version": self.schema_version,
            **{
                f"capability_provider_{kind}": provider
                for kind, provider in self.capability_provider_map.items()
            },
            "qwenpaw_enabled": self.qwenpaw_enabled,
            "qwenpaw_url": self.qwenpaw_url,
            "qwenpaw_agent_id": self.qwenpaw_agent_id,
            "qwenpaw_auto_start": self.qwenpaw_auto_start,
            "qwenpaw_python": self.qwenpaw_python,
            "qwenpaw_auth_token": self.qwenpaw_auth_token,
            "mcp_servers": dict(self.mcp_servers),
        }
