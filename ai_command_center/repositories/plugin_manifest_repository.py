"""Repository for plugin manifest file access and SQLite state persistence."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import yaml

from ai_command_center.core.plugin_manifest import PluginManifest


class PluginManifestRepository:
    """Owns plugin manifest persistence access and SQLite state persistence."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

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

    def load_enabled_states(self) -> dict[str, bool]:
        """Load persisted enabled states from SQLite."""
        if self._conn is None:
            return {}
        rows = self._conn.execute("SELECT plugin_id, enabled FROM plugin_state").fetchall()
        return {str(r["plugin_id"]): bool(r["enabled"]) for r in rows}

    def save_enabled_state(self, plugin_id: str, enabled: bool) -> None:
        """Persist a plugin's enabled state to SQLite."""
        if self._conn is None:
            return
        self._conn.execute(
            "INSERT INTO plugin_state (plugin_id, enabled, updated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(plugin_id) DO UPDATE SET enabled=excluded.enabled, updated_at=excluded.updated_at",
            (plugin_id, 1 if enabled else 0, time.time()),
        )
        self._conn.commit()

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
            service=str(data.get("service", "")),
        )
