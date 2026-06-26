"""Declarative plugin manifests — no dynamic code loading (Phase 5B)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PluginManifest:
    id: str
    name: str
    version: str
    description: str
    kind: str  # core | extension
    bus_topics: tuple[str, ...]
    enabled: bool = True
    service: str = ""  # primary service to restart when toggled

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "kind": self.kind,
            "bus_topics": list(self.bus_topics),
            "enabled": self.enabled,
            "service": self.service,
        }
