"""Settings repository compatibility re-export.

The canonical SQLite-backed implementation lives in
`ai_command_center.repositories.settings_repository`. This module re-exports it
so that `core.settings.settings_service` can import the canonical repository
without duplication.
"""

from __future__ import annotations

from ai_command_center.repositories.settings_repository import SettingsRepository

__all__ = ["SettingsRepository"]
