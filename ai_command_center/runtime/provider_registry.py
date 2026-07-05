"""Registry of Agent Runtime Interface providers."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.runtime.agent_runtime_provider import AgentRuntimeProvider
from ai_command_center.runtime.providers.native_provider import NativeRuntimeProvider
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState
from ai_command_center.runtime.providers.qwenpaw_sidecar_provider import (
    QwenPawSidecarProvider,
)


class RuntimeProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, AgentRuntimeProvider] = {}

    def register(self, provider: AgentRuntimeProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> AgentRuntimeProvider | None:
        return self._providers.get(provider_id)

    def list_ids(self) -> list[str]:
        return sorted(self._providers)

    def resolve_for_kind(self, kind: CapabilityKind, provider_id: str) -> AgentRuntimeProvider | None:
        provider = self.get(provider_id)
        if provider is None:
            return None
        if not provider.supports(kind):
            return None
        return provider


def build_default_runtime_registry(
    bus: EventBus | None = None,
    *,
    qwenpaw_health: QwenPawSidecarHealthState | None = None,
) -> RuntimeProviderRegistry:
    registry = RuntimeProviderRegistry()
    registry.register(NativeRuntimeProvider())
    registry.register(
        QwenPawSidecarProvider(bus=bus, health_state=qwenpaw_health or QwenPawSidecarHealthState())
    )
    return registry
