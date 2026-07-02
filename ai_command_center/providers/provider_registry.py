"""Registry for LLM providers — register, list, and describe by name."""

from __future__ import annotations

from typing import Any

from ai_command_center.providers.llm_provider import LLMProvider


class ProviderRegistry:
    """In-memory registry of LLM provider metadata."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        """Register a provider by its canonical name."""
        self._providers[provider.info.name] = provider

    def get(self, name: str) -> LLMProvider | None:
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        return sorted(self._providers)

    def describe(self, name: str) -> dict[str, Any] | None:
        provider = self._providers.get(name)
        if provider is None:
            return None
        return provider.describe()

    def list_descriptions(self) -> list[dict[str, Any]]:
        return [p.describe() for p in self._providers.values()]

    def resolve_for_model(self, model: str, *, provider: str | None = None) -> str | None:
        """Return provider name that supports the model, preferring ``provider`` when valid."""
        if provider and provider in self._providers:
            candidate = self._providers[provider]
            if candidate.supports(model):
                return provider
        for name, registered in self._providers.items():
            if registered.supports(model):
                return name
        return provider if provider in self._providers else None


def build_default_registry() -> ProviderRegistry:
    """Create a registry pre-populated with built-in provider descriptors."""
    from ai_command_center.providers.builtin import OllamaProviderDescriptor, OpenAIProviderDescriptor

    registry = ProviderRegistry()
    registry.register(OllamaProviderDescriptor())
    registry.register(OpenAIProviderDescriptor())
    return registry
