"""Provider default model helpers."""

from __future__ import annotations

from ai_command_center.providers.provider_registry import ProviderRegistry, build_default_registry


def default_model_for_provider(
    provider: str,
    registry: ProviderRegistry | None = None,
) -> str:
    reg = registry or build_default_registry()
    info = reg.describe(provider)
    if info and info.get("default_model"):
        return str(info["default_model"])
    return "llama3.2:3b"


def provider_display_name(provider: str, registry: ProviderRegistry | None = None) -> str:
    reg = registry or build_default_registry()
    info = reg.describe(provider)
    if info and info.get("display_name"):
        return str(info["display_name"])
    return provider
