"""Stub echo runtime provider for ARI Phase 5 tests."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import CAPABILITY_COMPLETE
from ai_command_center.domain.runtime_capability import (
    CapabilityKind,
    ProviderHealth,
    ProviderHealthState,
    RuntimeInvocationRequest,
)


class StubEchoProvider:
    """Test provider that echoes query text back via capability.complete."""

    provider_id = "stub_echo"

    _SUPPORTED = frozenset({CapabilityKind.CHAT})

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus

    def health(self) -> ProviderHealth:
        return ProviderHealth(state=ProviderHealthState.READY, detail="stub echo ready")

    def supports(self, kind: CapabilityKind) -> bool:
        return kind in self._SUPPORTED

    def invoke(self, request: RuntimeInvocationRequest) -> None:
        if self._bus is None:
            return
        self._bus.publish(
            CAPABILITY_COMPLETE,
            {
                "request_id": request.request_id,
                "provider_id": self.provider_id,
                "kind": request.kind.value,
                "text": f"echo:{request.query}",
                "metadata": {"stub": True},
            },
            source=self.provider_id,
        )
