"""Native ACC runtime — chat and agents via existing bus handlers."""

from __future__ import annotations

from ai_command_center.domain.runtime_capability import (
    CapabilityKind,
    ProviderHealth,
    ProviderHealthState,
    RuntimeInvocationRequest,
)


class NativeRuntimeProvider:
    """Default provider. Chat/agents handled by existing services on command.routed."""

    provider_id = "native"

    _SUPPORTED = frozenset(
        {
            CapabilityKind.CHAT,
            CapabilityKind.PLANNING,
            CapabilityKind.CODING,
            CapabilityKind.RESEARCH,
            CapabilityKind.AUTOMATION,
            CapabilityKind.AGENTS,
            CapabilityKind.MEMORY,
        }
    )

    def health(self) -> ProviderHealth:
        return ProviderHealth(state=ProviderHealthState.READY)

    def supports(self, kind: CapabilityKind) -> bool:
        return kind in self._SUPPORTED

    def invoke(self, request: RuntimeInvocationRequest) -> None:
        """Native path is bus-delegated; ChatHandler listens to command.routed directly."""
