"""Settings schema migration tests (F2 M2)."""

from __future__ import annotations

import unittest

from ai_command_center.core.settings.migration_manager import MigrationManager
from ai_command_center.platform.model_registry import DEFAULT_MODEL_TIER_MAP


class SettingsMigrationTests(unittest.TestCase):
    def test_v1_payload_advances_to_latest_schema_version(self) -> None:
        migrated = MigrationManager().migrate({"schema_version": 1, "theme": "dark"})
        self.assertEqual(migrated["schema_version"], 6)
        self.assertEqual(migrated["provider"], "ollama")
        self.assertEqual(migrated["capability_provider_planning"], "qwenpaw")
        self.assertEqual(migrated["mcp_servers"], {})
        self.assertEqual(migrated["model_tier_map"], dict(DEFAULT_MODEL_TIER_MAP))

    def test_v3_payload_advances_to_schema_version_6(self) -> None:
        migrated = MigrationManager().migrate({"schema_version": 3, "theme": "dark"})
        self.assertEqual(migrated["schema_version"], 6)
        self.assertEqual(migrated["capability_provider_planning"], "qwenpaw")
        self.assertEqual(migrated["capability_provider_chat"], "native")

    def test_v2_payload_preserves_existing_values(self) -> None:
        original = {
            "schema_version": 2,
            "provider": "openai",
            "default_model": "gpt-4o",
        }
        migrated = MigrationManager().migrate(dict(original))
        self.assertEqual(migrated["schema_version"], 6)
        self.assertEqual(migrated["default_model"], "gpt-4o")
        self.assertEqual(migrated["provider"], "openai")


if __name__ == "__main__":
    unittest.main()
