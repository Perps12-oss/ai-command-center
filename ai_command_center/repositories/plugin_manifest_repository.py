"""Repository for plugin manifest file access."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_command_center.core.plugin_manifest import PluginManifest


class PluginManifestRepository:
    """Owns plugin manifest persistence access."""

    def list_manifests(self, manifests_dir: Path) -> list[PluginManifest]:
        manifests: list[PluginManifest] = []
        if not manifests_dir.is_dir():
            return manifests
        for path in sorted(manifests_dir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except OSError:
                continue
            manifest = self._parse_manifest(raw)
            if manifest is not None:
                manifests.append(manifest)
        return manifests

    @staticmethod
    def _parse_manifest(data: dict) -> PluginManifest | None:
        plugin_id = str(data.get("id", "")).strip()
        if not plugin_id:
            return None
        topics = data.get("bus_topics") or []
        return PluginManifest(
            id=plugin_id,
            name=str(data.get("name", plugin_id)),
            version=str(data.get("version", "1.0")),
            description=str(data.get("description", "")),
            kind=str(data.get("kind", "extension")),
            bus_topics=tuple(str(t) for t in topics),
            enabled=bool(data.get("enabled", True)),
        )
