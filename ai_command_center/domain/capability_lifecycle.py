"""Capability lifecycle domain contracts (Provider Platform v2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CapabilityLifecycleState(str, Enum):
    """Ordered lifecycle stages for a registered capability."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    CERTIFIED = "certified"
    HEALTHY = "healthy"
    OBSERVABLE = "observable"
    CALLABLE = "callable"
    TRUSTED = "trusted"
    EXPOSED = "exposed"


_LIFECYCLE_ORDER: tuple[CapabilityLifecycleState, ...] = tuple(CapabilityLifecycleState)


def max_lifecycle_state(*states: CapabilityLifecycleState) -> CapabilityLifecycleState:
    """Return the highest lifecycle stage among the given states."""
    if not states:
        return CapabilityLifecycleState.DISCOVERED
    return max(states, key=lambda state: _LIFECYCLE_ORDER.index(state))


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    """Canonical capability lifecycle record for control-plane projections."""

    capability_id: str
    provider_id: str
    lifecycle_state: CapabilityLifecycleState
    provider_ids: tuple[str, ...] = ()
    capability_kind: str = ""
    source: str = ""  # runtime | orchestration
    certified: bool = False
    observable: bool = False
    health_status: str = "offline"  # healthy | degraded | offline
    last_error: str = ""
    discovered_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "provider_id": self.provider_id,
            "provider_ids": list(self.provider_ids),
            "lifecycle_state": self.lifecycle_state.value,
            "capability_kind": self.capability_kind,
            "source": self.source,
            "certified": self.certified,
            "observable": self.observable,
            "health_status": self.health_status,
            "last_error": self.last_error,
            "discovered_at": self.discovered_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> CapabilityRecord:
        state_raw = str(payload.get("lifecycle_state", CapabilityLifecycleState.DISCOVERED.value))
        try:
            lifecycle_state = CapabilityLifecycleState(state_raw)
        except ValueError:
            lifecycle_state = CapabilityLifecycleState.DISCOVERED
        provider_ids_raw = payload.get("provider_ids") or ()
        provider_ids = tuple(str(item) for item in provider_ids_raw) if provider_ids_raw else ()
        return cls(
            capability_id=str(payload.get("capability_id", "")),
            provider_id=str(payload.get("provider_id", "")),
            lifecycle_state=lifecycle_state,
            provider_ids=provider_ids,
            capability_kind=str(payload.get("capability_kind", "")),
            source=str(payload.get("source", "")),
            certified=bool(payload.get("certified", False)),
            observable=bool(payload.get("observable", False)),
            health_status=str(payload.get("health_status", "offline")),
            last_error=str(payload.get("last_error", "")),
            discovered_at=float(payload.get("discovered_at", 0.0) or 0.0),
            updated_at=float(payload.get("updated_at", 0.0) or 0.0),
        )
