"""Immutable AppState snapshot for the Provider Registry.

Consolidates two existing AppState projections into one typed snapshot:
  provider_health_map            (tuple[ProviderHealthSnapshot])
  runtime_capability_providers   (tuple[RuntimeProviderItem])

Both are updated by CAPABILITY_PROVIDERS_READY and ORCHESTRATION_PROVIDER_HEALTH.
Consumers should prefer AppState.provider_registry over the raw fields.
The raw fields are retained for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderEntry:
    """Unified view of a single provider: identity + health + capabilities."""

    provider_id: str = ""
    name: str = ""
    version: str = ""
    source: str = ""         # "runtime" | "orchestration"
    kind: str = ""
    health_status: str = "offline"   # "healthy" | "degraded" | "offline"
    health_detail: str = ""
    enabled: bool = True
    capabilities: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()

    @property
    def healthy(self) -> bool:
        return self.health_status == "healthy"

    @property
    def degraded(self) -> bool:
        return self.health_status == "degraded"


@dataclass(frozen=True, slots=True)
class ProviderRegistrySnapshot:
    """Immutable AppState projection of all known providers."""

    providers: tuple[ProviderEntry, ...] = ()
    total_count: int = 0
    healthy_count: int = 0
    degraded_count: int = 0

    @property
    def offline_count(self) -> int:
        return self.total_count - self.healthy_count - self.degraded_count

    @property
    def healthy_providers(self) -> tuple[ProviderEntry, ...]:
        return tuple(p for p in self.providers if p.healthy)

    @property
    def runtime_providers(self) -> tuple[ProviderEntry, ...]:
        return tuple(p for p in self.providers if p.source == "runtime")

    @property
    def orchestration_providers(self) -> tuple[ProviderEntry, ...]:
        return tuple(p for p in self.providers if p.source == "orchestration")

    def by_id(self, provider_id: str) -> ProviderEntry | None:
        for p in self.providers:
            if p.provider_id == provider_id:
                return p
        return None
