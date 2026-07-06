"""Repository for runtime provider manifest YAML and SQLite enabled state."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import yaml

from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest


class RuntimeProviderManifestRepository:
    """Owns runtime provider manifest file access and plugin_state persistence."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

    def list_manifests(self, manifests_dir: Path) -> list[RuntimeProviderManifest]:
        manifests: list[RuntimeProviderManifest] = []
        if not manifests_dir.is_dir():
            return manifests
        for path in sorted(manifests_dir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            manifest = self.parse_manifest(raw)
            if manifest is not None:
                manifests.append(manifest)
        return manifests

    def load_enabled_states(self) -> dict[str, bool]:
        if self._conn is None:
            return {}
        rows = self._conn.execute("SELECT plugin_id, enabled FROM plugin_state").fetchall()
        return {str(r["plugin_id"]): bool(r["enabled"]) for r in rows}

    def save_enabled_state(self, provider_id: str, enabled: bool) -> None:
        if self._conn is None:
            return
        self._conn.execute(
            "INSERT INTO plugin_state (plugin_id, enabled, updated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(plugin_id) DO UPDATE SET enabled=excluded.enabled, updated_at=excluded.updated_at",
            (provider_id, 1 if enabled else 0, time.time()),
        )
        self._conn.commit()

    @staticmethod
    def parse_manifest(data: dict) -> RuntimeProviderManifest | None:
        provider_id = str(data.get("id", "")).strip()
        if not provider_id:
            return None
        entrypoint = str(data.get("entrypoint", "")).strip()
        if not entrypoint:
            return None
        raw_caps = data.get("capabilities") or []
        capabilities: list[CapabilityKind] = []
        for item in raw_caps:
            try:
                capabilities.append(CapabilityKind(str(item).strip().lower()))
            except ValueError:
                continue
        if not capabilities:
            return None
        return RuntimeProviderManifest(
            id=provider_id,
            name=str(data.get("name", provider_id)),
            version=str(data.get("version", "1.0")),
            description=str(data.get("description", "")),
            entrypoint=entrypoint,
            capabilities=tuple(capabilities),
            enabled=bool(data.get("enabled", True)),
            kind=str(data.get("kind", "runtime_provider")),
            permissions=tuple(str(p) for p in (data.get("permissions") or [])),
            events=tuple(str(e) for e in (data.get("events") or [])),
            health_probe=str(data.get("health_probe", "")),
            dependencies=tuple(str(d) for d in (data.get("dependencies") or [])),
            certification_level=str(data.get("certification_level", "")),
            min_sdk_version=str(data.get("min_sdk_version", "1.0")),
        )
