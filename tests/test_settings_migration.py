"""Settings schema migration tests (F2 M2)."""

from __future__ import annotations

import unittest

from ai_command_center.core.settings.migration_manager import MigrationManager


class SettingsMigrationTests(unittest.TestCase):
    def test_v1_payload_advances_to_schema_version_2(self) -> None:
        migrated = MigrationManager().migrate({"schema_version": 1, "theme": "dark"})
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["provider"], "ollama")

    def test_v2_payload_is_not_re_migrated(self) -> None:
        original = {
            "schema_version": 2,
            "provider": "openai",
            "default_model": "gpt-4o",
        }
        migrated = MigrationManager().migrate(dict(original))
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["default_model"], "gpt-4o")


if __name__ == "__main__":
    unittest.main()
