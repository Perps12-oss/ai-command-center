"""Canonical plugin manifest contract."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str = "1.0"
    enabled: bool = False
    capabilities: tuple[str, ...] = field(default_factory=tuple)
