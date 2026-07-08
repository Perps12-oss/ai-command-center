"""Runtime provider plugin manifest domain model (ARI Phase 5 + Provider Platform Epic 8)."""

from __future__ import annotations

from dataclasses import dataclass

from ai_command_center.domain.runtime_capability import CapabilityKind


@dataclass(frozen=True, slots=True)
class RuntimeProviderManifest:
    """Declarative manifest for an ARI runtime provider plugin."""

    id: str
    name: str
    version: str
    description: str
    entrypoint: str
    capabilities: tuple[CapabilityKind, ...]
    enabled: bool = True
    kind: str = "runtime_provider"
    permissions: tuple[str, ...] = ()
    events: tuple[str, ...] = ()
    health_probe: str = ""
    dependencies: tuple[str, ...] = ()
    certification_level: str = ""
    min_sdk_version: str = "1.0"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "entrypoint": self.entrypoint,
            "capabilities": [c.value for c in self.capabilities],
            "enabled": self.enabled,
            "kind": self.kind,
            "permissions": list(self.permissions),
            "events": list(self.events),
            "health_probe": self.health_probe,
            "dependencies": list(self.dependencies),
            "certification_level": self.certification_level,
            "min_sdk_version": self.min_sdk_version,
        }
