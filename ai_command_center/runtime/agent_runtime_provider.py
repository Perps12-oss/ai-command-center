"""Agent Runtime Provider protocol (ARI)."""

from __future__ import annotations

from typing import Protocol

from ai_command_center.domain.runtime_capability import (
    CapabilityKind,
    ProviderHealth,
    RuntimeInvocationRequest,
)


class AgentRuntimeProvider(Protocol):
    """Capability backend — sidecar or native. Bus-native; no direct UI access."""

    provider_id: str

    def health(self) -> ProviderHealth: ...

    def supports(self, kind: CapabilityKind) -> bool: ...

    def invoke(self, request: RuntimeInvocationRequest) -> None: ...
