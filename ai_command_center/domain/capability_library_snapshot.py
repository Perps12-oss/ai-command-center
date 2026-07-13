"""Immutable AppState snapshot for the Capability Library.

Consolidates three existing AppState projections into one typed snapshot:
  capability_lifecycle    (from CAPABILITY_LIFECYCLE_SNAPSHOT)
  capability_prompt_catalog (from CAPABILITY_CATALOG_RESULT)
  runtime_capability_providers health (from CAPABILITY_PROVIDERS_READY)

Consumers should prefer AppState.capability_library over the raw tuple fields.
The raw fields are retained for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CapabilityEntry:
    """Unified view of a single capability across lifecycle and catalog layers."""

    capability_id: str = ""
    provider_id: str = ""
    capability_kind: str = ""
    lifecycle_state: str = "discovered"
    health_status: str = "offline"
    certified: bool = False
    observable: bool = False
    source: str = ""
    description: str = ""
    parameters: tuple[tuple[str, str], ...] = ()
    last_error: str = ""
    discovered_at: float = 0.0
    updated_at: float = 0.0


@dataclass(frozen=True, slots=True)
class ProviderEntry:
    """Lightweight runtime provider summary within the library snapshot."""

    provider_id: str = ""
    name: str = ""
    version: str = ""
    health_state: str = ""
    enabled: bool = True
    capability_count: int = 0


@dataclass(frozen=True, slots=True)
class CapabilityLibrarySnapshot:
    """Immutable AppState projection of the full capability library."""

    entries: tuple[CapabilityEntry, ...] = ()
    providers: tuple[ProviderEntry, ...] = ()
    total_count: int = 0
    healthy_count: int = 0
    catalog_version: int = 0

    @property
    def callable_entries(self) -> tuple[CapabilityEntry, ...]:
        return tuple(e for e in self.entries if e.lifecycle_state in {"callable", "trusted", "exposed"})

    @property
    def healthy_entries(self) -> tuple[CapabilityEntry, ...]:
        return tuple(e for e in self.entries if e.health_status == "healthy")

    def by_id(self, capability_id: str) -> CapabilityEntry | None:
        for e in self.entries:
            if e.capability_id == capability_id:
                return e
        return None

    def by_provider(self, provider_id: str) -> tuple[CapabilityEntry, ...]:
        return tuple(e for e in self.entries if e.provider_id == provider_id)
