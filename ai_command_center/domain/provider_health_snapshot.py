"""Canonical provider health projection for diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderHealthSnapshot:
    """Unified health surface for orchestration and runtime providers."""

    provider_id: str
    status: str  # healthy | degraded | offline
    detail: str = ""
    source: str = ""  # orchestration | runtime
    kind: str = ""
    display_name: str = ""

    @property
    def healthy(self) -> bool:
        return self.status == "healthy"

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "status": self.status,
            "detail": self.detail,
            "source": self.source,
            "kind": self.kind,
            "display_name": self.display_name,
        }

    @staticmethod
    def from_runtime_payload(payload: dict[str, object]) -> ProviderHealthSnapshot:
        health_state = str(payload.get("health_state", "unavailable")).lower()
        if health_state in {"ready", "healthy"}:
            status = "healthy"
        elif health_state in {"degraded"}:
            status = "degraded"
        else:
            status = "offline"
        return ProviderHealthSnapshot(
            provider_id=str(payload.get("id", "")),
            status=status,
            detail=str(payload.get("health_detail", "")),
            source="runtime",
            kind=str(payload.get("kind", "")),
            display_name=str(payload.get("name", payload.get("id", ""))),
        )

    @staticmethod
    def from_orchestration_payload(payload: dict[str, object]) -> ProviderHealthSnapshot:
        healthy = bool(payload.get("healthy", False))
        return ProviderHealthSnapshot(
            provider_id=str(payload.get("provider_id", "")),
            status="healthy" if healthy else "offline",
            detail=str(payload.get("detail", "")),
            source="orchestration",
            display_name=str(payload.get("display_name", payload.get("provider_id", ""))),
        )
