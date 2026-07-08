"""Per-capability provider settings and router integration (ARI Phase 4)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CAPABILITY_CLASSIFIED,
    COMMAND_ROUTED,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.db.connection import connect, init_database
from ai_command_center.domain.capability_provider_settings import (
    DEFAULT_CAPABILITY_PROVIDER_MAP,
    settings_key_for_kind,
)
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.platform.model_registry import DEFAULT_MODEL_TIER_MAP
from ai_command_center.repositories.settings_repository import SettingsRepository
from ai_command_center.services.runtime_capability_router_service import RuntimeCapabilityRouterService
from ai_command_center.services.settings_service import SettingsService


def test_settings_round_trip_capability_providers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "settings.db"
        db = connect(db_path)
        init_database(db)
        try:
            bus = EventBus()
            service = SettingsService(bus, SettingsRepository(db))
            service.load()
            service.set(settings_key_for_kind("planning"), "native")
            service.set(settings_key_for_kind("coding"), "auto")
            snap = service.get_snapshot()
            assert snap.capability_provider_map["planning"] == "native"
            assert snap.capability_provider_map["coding"] == "auto"
            assert snap.schema_version >= 4
        finally:
            db.close()


def test_migration_v3_advances_to_v6_with_defaults() -> None:
    from ai_command_center.core.settings.migration_manager import MigrationManager

    migrated = MigrationManager().migrate({"schema_version": 3, "theme": "dark"})
    assert migrated["schema_version"] == 6
    assert migrated["mcp_servers"] == {}
    assert migrated["model_tier_map"] == dict(DEFAULT_MODEL_TIER_MAP)
    for kind, default in DEFAULT_CAPABILITY_PROVIDER_MAP.items():
        assert migrated[settings_key_for_kind(kind)] == default


def test_router_respects_user_provider_map() -> None:
    bus = EventBus()
    router = RuntimeCapabilityRouterService(bus)
    classified: list[dict] = []
    bus.subscribe(CAPABILITY_CLASSIFIED, lambda e: classified.append(dict(e.payload)))
    router.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {
                **{settings_key_for_kind(k): v for k, v in DEFAULT_CAPABILITY_PROVIDER_MAP.items()},
                settings_key_for_kind("planning"): "native",
            },
            source="settings",
        )
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "args": {"prompt": "plan my week"},
                "request_id": "req-user-map",
            },
            source="command_router",
        )
        assert len(classified) == 1
        assert classified[0]["kind"] == CapabilityKind.PLANNING.value
        assert classified[0]["provider_id"] == "native"
    finally:
        router.stop()


def test_auto_resolves_kind_specific_default() -> None:
    bus = EventBus()
    router = RuntimeCapabilityRouterService(bus)
    router.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {
                **{settings_key_for_kind(k): "auto" for k in DEFAULT_CAPABILITY_PROVIDER_MAP},
            },
            source="settings",
        )
        assert router.resolve_provider(CapabilityKind.PLANNING) == "qwenpaw"
        assert router.resolve_provider(CapabilityKind.CODING) == "qwenpaw"
        assert router.resolve_provider(CapabilityKind.CHAT) == "native"
        assert router.resolve_provider(CapabilityKind.RESEARCH) == "native"
    finally:
        router.stop()


def test_router_without_snapshot_uses_auto_defaults() -> None:
    bus = EventBus()
    router = RuntimeCapabilityRouterService(bus)
    router.start()
    try:
        assert router.resolve_provider(CapabilityKind.PLANNING) == "qwenpaw"
        assert router.resolve_provider(CapabilityKind.CHAT) == "native"
    finally:
        router.stop()


class CapabilityProviderSettingsTests(unittest.TestCase):
    def test_settings_service_persists_capability_provider_keys(self) -> None:
        test_settings_round_trip_capability_providers()


if __name__ == "__main__":
    unittest.main()
