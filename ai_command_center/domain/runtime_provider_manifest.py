"""Runtime provider plugin manifest domain model (ARI Phase 5)."""

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
        }
