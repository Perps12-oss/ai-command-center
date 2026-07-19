"""QwenPaw sidecar provider — delegates HTTP/SSE to QwenPawSidecarService.

Must not publish CAPABILITY_RUNTIME_REQUEST — ExecutionOrchestratorService is
the exclusive publisher of that topic.
"""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import CAPABILITY_ERROR
from ai_command_center.domain.runtime_capability import (
    CapabilityKind,
    ProviderHealth,
    ProviderHealthState,
    RuntimeInvocationRequest,
)
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState

_DEFAULT_HEALTH = QwenPawSidecarHealthState()


class QwenPawSidecarProvider:
    """External capability backend (planning, coding, agents)."""

    provider_id = "qwenpaw"

    _SUPPORTED = frozenset(
        {
            CapabilityKind.PLANNING,
            CapabilityKind.CODING,
            CapabilityKind.RESEARCH,
            CapabilityKind.AGENTS,
        }
    )

    def __init__(
        self,
        bus: EventBus | None = None,
        *,
        health_state: QwenPawSidecarHealthState | None = None,
    ) -> None:
        self._bus = bus
        self._health_state = health_state or _DEFAULT_HEALTH

    def health(self) -> ProviderHealth:
        enabled, reachable, detail = self._health_state.snapshot()
        if not enabled:
            return ProviderHealth(
                state=ProviderHealthState.UNAVAILABLE,
                detail="QwenPaw sidecar disabled in settings",
            )
        if reachable:
            return ProviderHealth(state=ProviderHealthState.READY, detail=detail)
        return ProviderHealth(
            state=ProviderHealthState.UNAVAILABLE,
            detail=detail or "QwenPaw sidecar unreachable",
        )

    def supports(self, kind: CapabilityKind) -> bool:
        return kind in self._SUPPORTED

    def invoke(self, request: RuntimeInvocationRequest) -> None:
        """Direct invoke is demoted — orchestrator owns CAPABILITY_RUNTIME_REQUEST."""
        if self._bus is None:
            return
        health = self.health()
        message = health.detail or "QwenPaw sidecar unavailable"
        if health.state == ProviderHealthState.READY:
            message = (
                "QwenPawSidecarProvider.invoke must not publish "
                "CAPABILITY_RUNTIME_REQUEST; route via ExecutionOrchestrator"
            )
        self._bus.publish(
            CAPABILITY_ERROR,
            {
                "request_id": request.request_id,
                "provider_id": self.provider_id,
                "kind": request.kind.value,
                "message": message,
            },
            source=self.provider_id,
        )
