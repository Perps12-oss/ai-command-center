"""Tests for Track 6.3 — Plugin Framework v2.

Covers:
- Persisted plugin enabled/disabled state
- Core plugin disable protection
- Extension plugin restart request via EventBus
- ServiceManager restart handling
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    PLUGIN_CATALOG,
    PLUGIN_DISABLE_REQUEST,
    PLUGIN_ENABLE_REQUEST,
    PLUGIN_ERROR,
    PLUGIN_STATE_CHANGED,
    SERVICE_RESTART_REQUEST,
    SERVICE_STATE_CHANGED,
)
from ai_command_center.core.plugin_manifest import PluginManifest
from ai_command_center.core.service_manager import ServiceManager
from ai_command_center.repositories.plugin_manifest_repository import (
    PluginManifestRepository,
)
from ai_command_center.services.base import BaseService
from ai_command_center.services.plugin_registry_service import PluginRegistryService


class _DummyService(BaseService):
    name = "dummy"

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self.stop_count = 0
        self.start_count = 0

    def _on_load(self) -> None:
        self.start_count += 1

    def _on_unload(self) -> None:
        self.stop_count += 1


class _PluginManifestRepository(PluginManifestRepository):
    """In-memory repository for tests with optional SQLite state."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        super().__init__(conn)
        self._manifests: list[PluginManifest] = []

    def add_manifest(self, manifest: PluginManifest) -> None:
        self._manifests.append(manifest)

    def list_manifests(self, manifests_dir: Path) -> list[PluginManifest]:
        return list(self._manifests)


class PluginStatePersistenceTests(unittest.TestCase):
    def test_persisted_state_overrides_manifest_default(self) -> None:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE plugin_state (plugin_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.execute(
            "INSERT INTO plugin_state (plugin_id, enabled, updated_at) VALUES (?, ?, ?)",
            ("ext", 0, time.time()),
        )
        conn.commit()

        repo = _PluginManifestRepository(conn)
        repo.add_manifest(
            PluginManifest(
                id="ext",
                name="Extension",
                version="1.0",
                description="",
                kind="extension",
                bus_topics=(),
                enabled=True,
                service="dummy",
            )
        )

        bus = EventBus(debug_mode=True)
        catalogs: list[dict] = []
        bus.subscribe(PLUGIN_CATALOG, lambda e: catalogs.append(dict(e.payload)))
        registry = PluginRegistryService(bus, repo=repo)
        registry.load()

        self.assertTrue(catalogs)
        plugins = {p["id"]: p for p in catalogs[-1].get("plugins", [])}
        self.assertFalse(plugins["ext"]["enabled"])

        registry.unload()

    def test_state_is_saved_on_disable(self) -> None:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE plugin_state (plugin_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.commit()

        repo = _PluginManifestRepository(conn)
        repo.add_manifest(
            PluginManifest(
                id="ext",
                name="Extension",
                version="1.0",
                description="",
                kind="extension",
                bus_topics=(),
                enabled=True,
                service="dummy",
            )
        )

        bus = EventBus(debug_mode=True)
        registry = PluginRegistryService(bus, repo=repo)
        registry.load()
        bus.publish(PLUGIN_DISABLE_REQUEST, {"id": "ext"}, source="test")
        time.sleep(0.05)

        row = conn.execute(
            "SELECT enabled FROM plugin_state WHERE plugin_id = ?", ("ext",)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["enabled"], 0)

        registry.unload()


class PluginCoreProtectionTests(unittest.TestCase):
    def test_core_plugin_disable_emits_error(self) -> None:
        repo = _PluginManifestRepository()
        repo.add_manifest(
            PluginManifest(
                id="core",
                name="Core",
                version="1.0",
                description="",
                kind="core",
                bus_topics=(),
                enabled=True,
            )
        )

        bus = EventBus(debug_mode=True)
        seen: list[str] = []
        bus.subscribe(PLUGIN_ERROR, lambda e: seen.append(e.payload.get("message", "")))

        registry = PluginRegistryService(bus, repo=repo)
        registry.load()
        bus.publish(PLUGIN_DISABLE_REQUEST, {"id": "core"}, source="test")
        time.sleep(0.05)

        self.assertTrue(any("core plugin cannot be disabled" in m for m in seen))
        registry.unload()


class PluginRestartRequestTests(unittest.TestCase):
    def test_extension_disable_requests_service_restart(self) -> None:
        repo = _PluginManifestRepository()
        repo.add_manifest(
            PluginManifest(
                id="ext",
                name="Extension",
                version="1.0",
                description="",
                kind="extension",
                bus_topics=(),
                enabled=True,
                service="dummy",
            )
        )

        bus = EventBus(debug_mode=True)
        restart_events: list[dict] = []
        bus.subscribe(
            SERVICE_RESTART_REQUEST,
            lambda e: restart_events.append(dict(e.payload)),
        )

        registry = PluginRegistryService(bus, repo=repo)
        registry.load()
        bus.publish(PLUGIN_DISABLE_REQUEST, {"id": "ext"}, source="test")
        time.sleep(0.05)

        self.assertEqual(len(restart_events), 1)
        self.assertEqual(restart_events[0].get("service"), "dummy")
        registry.unload()


class ServiceManagerRestartTests(unittest.TestCase):
    def test_service_manager_restarts_service_on_request(self) -> None:
        bus = EventBus(debug_mode=True)
        manager = ServiceManager(bus)
        service = _DummyService(bus)
        manager.register(service)
        manager.load_all()

        self.assertEqual(service.start_count, 1)
        self.assertEqual(service.stop_count, 0)

        bus.publish(SERVICE_RESTART_REQUEST, {"service": "dummy"}, source="test")
        time.sleep(0.05)

        self.assertEqual(service.start_count, 2)
        self.assertEqual(service.stop_count, 1)

        manager.shutdown()

