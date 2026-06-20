"""Telemetry repository wrapper for the new architecture package."""

from __future__ import annotations

import sqlite3

from ai_command_center.db.telemetry_repository import TelemetryRepository as DbTelemetryRepository


class TelemetryRepository(DbTelemetryRepository):
    """Compatibility wrapper that exposes the repository contract via the new package."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(conn)
