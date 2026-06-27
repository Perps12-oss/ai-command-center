"""Tests for the consolidated settings event pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    SETTINGS_CHANGED,
    SETTINGS_SNAPSHOT,
    SETTINGS_UPDATED,
)
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.settings_repository import SettingsRepository
from ai_command_center.services.settings_service import SettingsService


@pytest.fixture
def settings_service():
    db = init_database(connect(Path(":memory:")))
    bus = EventBus()
    repo = SettingsRepository(db)
    service = SettingsService(bus, repo)
    service.start()
    yield service
    service.stop()


def test_set_emits_single_updated_and_snapshot_event(settings_service: SettingsService) -> None:
    """The bus-facing service emits exactly one SETTINGS_UPDATED and one SETTINGS_SNAPSHOT per change."""
    bus = settings_service._bus
    events: list = []
    bus.subscribe(SETTINGS_UPDATED, events.append)
    bus.subscribe(SETTINGS_SNAPSHOT, events.append)
    bus.subscribe(SETTINGS_CHANGED, events.append)

    settings_service.set("theme", "light")

    updated = [e for e in events if e.topic == SETTINGS_UPDATED]
    snapshots = [e for e in events if e.topic == SETTINGS_SNAPSHOT]
    changed = [e for e in events if e.topic == SETTINGS_CHANGED]

    assert len(updated) == 1
    assert len(snapshots) == 1
    assert len(changed) == 0
    assert updated[0].payload["key"] == "theme"
    assert updated[0].payload["value"] == "light"


def test_set_returns_validated_value(settings_service: SettingsService) -> None:
    """Boolean-like settings are coerced by the schema."""
    validated = settings_service._core_settings.set("low_memory_mode", "true")
    assert validated is True
