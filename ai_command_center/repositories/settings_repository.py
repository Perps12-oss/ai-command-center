"""Settings repository wrapper for the new architecture package."""

from __future__ import annotations

import sqlite3

from ai_command_center.db.repository import SettingsRepository as DbSettingsRepository


class SettingsRepository(DbSettingsRepository):
    """Compatibility wrapper that exposes the repository contract via the new package."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(conn)
