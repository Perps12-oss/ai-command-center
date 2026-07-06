"""Migration support for settings."""

from __future__ import annotations

from typing import Any

from ai_command_center.domain.capability_provider_settings import (
    DEFAULT_CAPABILITY_PROVIDER_MAP,
    settings_key_for_kind,
)


class MigrationManager:
    """Applies simple schema migrations for settings payloads."""

    def migrate(self, payload: dict[str, Any]) -> dict[str, Any]:
        schema_version = int(payload.get("schema_version", 1))
        if schema_version < 2:
            payload = dict(payload)
            payload.setdefault("provider", "ollama")
            payload.setdefault("openai_base_url", "https://api.openai.com/v1")
            payload.setdefault("openai_api_key", "")
            payload["schema_version"] = 2
            schema_version = 2
        if schema_version < 3:
            payload = dict(payload)
            payload.setdefault("qwenpaw_enabled", False)
            payload.setdefault("qwenpaw_url", "http://127.0.0.1:8088")
            payload.setdefault("qwenpaw_agent_id", "default")
            payload.setdefault("qwenpaw_auto_start", False)
            payload.setdefault("qwenpaw_python", "")
            payload.setdefault("qwenpaw_auth_token", "")
            payload["schema_version"] = 3
            schema_version = 3
        if schema_version < 4:
            payload = dict(payload)
            for kind, default in DEFAULT_CAPABILITY_PROVIDER_MAP.items():
                payload.setdefault(settings_key_for_kind(kind), default)
            payload["schema_version"] = 4
            schema_version = 4
        if schema_version < 5:
            payload = dict(payload)
            payload.setdefault("mcp_servers", {})
            payload["schema_version"] = 5
        return payload
