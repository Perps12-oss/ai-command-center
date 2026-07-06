"""Adapters bridging orchestration/runtime providers to the SDK surface."""

from __future__ import annotations

from ai_command_center.orchestration.providers.provider_protocol import OrchestrationProvider
from ai_command_center.provider_sdk.base import CertifiableProvider
from ai_command_center.runtime.agent_runtime_provider import AgentRuntimeProvider


class OrchestrationProviderAdapter:
    """Wrap an orchestration provider for SDK certification."""

    def __init__(self, provider: OrchestrationProvider) -> None:
        self._provider = provider

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def health(self) -> tuple[bool, str]:
        return self._provider.health()


class RuntimeProviderAdapter:
    """Wrap a runtime provider for SDK certification."""

    def __init__(self, provider: AgentRuntimeProvider) -> None:
        self._provider = provider

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def health(self) -> tuple[bool, str]:
        result = self._provider.health()
        healthy = result.state.value in {"ready", "healthy"}
        return healthy, result.detail


def as_certifiable(provider: object) -> CertifiableProvider:
    if isinstance(provider, OrchestrationProviderAdapter):
        return provider
    if isinstance(provider, RuntimeProviderAdapter):
        return provider
    if hasattr(provider, "provider_id") and hasattr(provider, "health"):
        return provider  # type: ignore[return-value]
    raise TypeError(f"unsupported provider type: {type(provider)!r}")
