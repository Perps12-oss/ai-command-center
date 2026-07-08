"""Settings provider switch behavior (F2 M2)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.settings_repository import SettingsRepository
from ai_command_center.services.settings_service import SettingsService


class SettingsProviderSwitchTests(unittest.TestCase):
    def test_switching_provider_updates_default_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "settings.db"
            db = connect(db_path)
            init_database(db)
            try:
                bus = EventBus(debug_mode=True)
                service = SettingsService(bus, SettingsRepository(db))
                service.load()
                service.set("default_model", "llama3.2:3b")
                service.set("provider", "openai")
                snap = service.get_snapshot()
                self.assertEqual(snap.provider, "openai")
                self.assertEqual(snap.default_model, "gpt-4o-mini")
                self.assertEqual(snap.summarize_model, "gpt-4o-mini")
            finally:
                db.close()

    def test_model_tier_map_round_trips_through_settings_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "settings.db"
            db = connect(db_path)
            init_database(db)
            try:
                bus = EventBus(debug_mode=True)
                service = SettingsService(bus, SettingsRepository(db))
                service.load()
                service.set(
                    "model_tier_map",
                    {"entity:note": "qwen2.5:7b", "summarize": "llama3.1:8b"},
                )
                snap = service.get_snapshot()
                self.assertEqual("qwen2.5:7b", snap.model_tier_map["entity:note"])
                self.assertEqual("llama3.1:8b", snap.to_payload()["model_tier_map"]["summarize"])
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
