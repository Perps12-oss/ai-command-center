"""Data access layer."""

from __future__ import annotations

import sqlite3
from typing import Any


class SettingsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    def ensure_defaults(self, defaults: dict[str, str]) -> None:
        for key, value in defaults.items():
            exists = self._conn.execute(
                "SELECT 1 FROM settings WHERE key = ?", (key,)
            ).fetchone()
            if exists is None:
                self.set(key, value)

    def all_settings(self) -> dict[str, str]:
        rows = self._conn.execute("SELECT key, value FROM settings").fetchall()
        return {str(r["key"]): str(r["value"]) for r in rows}

    def get_all(self) -> dict[str, str]:
        """Compatibility alias for core settings service."""
        return self.all_settings()


class ConversationRepository:
    """Deprecated import path — use db.conversation_repository."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        from ai_command_center.db.conversation_repository import (
            ConversationRepository as _Repo,
        )

        self._repo = _Repo(conn)

    def count(self) -> int:
        return self._repo.message_count()
