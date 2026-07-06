"""Orchestration provider manifest domain model (Provider Platform Epic 8)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OrchestrationProviderManifest:
    """Declarative manifest for a truth-bound orchestration provider."""

    id: str
    name: str
    version: str
    description: str
    intents: tuple[str, ...]
    permissions: tuple[str, ...] = ()
    events: tuple[str, ...] = ()
    health_probe: str = ""
    dependencies: tuple[str, ...] = ()
    certification_level: str = ""
    min_sdk_version: str = "1.0"
    enabled: bool = True
    kind: str = "orchestration_provider"
    entrypoint: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "intents": list(self.intents),
            "permissions": list(self.permissions),
            "events": list(self.events),
            "health_probe": self.health_probe,
            "dependencies": list(self.dependencies),
            "certification_level": self.certification_level,
            "min_sdk_version": self.min_sdk_version,
            "enabled": self.enabled,
            "kind": self.kind,
            "entrypoint": self.entrypoint,
        }
