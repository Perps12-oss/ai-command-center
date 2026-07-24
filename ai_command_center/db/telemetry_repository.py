"""Passive telemetry persistence — append-only event log.

.. deprecated::
    Import ``TelemetryRepository`` from ``ai_command_center.repositories`` instead.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ai_command_center.db.conn_sync import connection_lock
from ai_command_center.domain.telemetry_event import TelemetryEvent


def _utc_iso(ts: float | None = None) -> str:
    when = datetime.fromtimestamp(ts or datetime.now(timezone.utc).timestamp(), tz=timezone.utc)
    return when.isoformat()


class TelemetryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, event: str, payload: dict[str, Any], *, timestamp: str | None = None) -> None:
        self.insert_many([(event, payload, timestamp)])

    def insert_many(
        self,
        rows: list[tuple[str, dict[str, Any], str | None]],
    ) -> None:
        """Batch-insert telemetry rows with a single commit."""
        if not rows:
            return
        prepared: list[tuple[str, str, str]] = []
        for event, payload, timestamp in rows:
            prepared.append(
                (
                    event,
                    timestamp or _utc_iso(),
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                )
            )
        with connection_lock(self._conn):
            self._conn.executemany(
                "INSERT INTO telemetry_events (event, timestamp, payload) VALUES (?, ?, ?)",
                prepared,
            )
            self._conn.commit()

    def fetch_since(self, since_iso: str) -> list[TelemetryEvent]:
        with connection_lock(self._conn):
            rows = self._conn.execute(
                """
                SELECT event, timestamp, payload
                FROM telemetry_events
                WHERE timestamp >= ?
                ORDER BY id ASC
                """,
                (since_iso,),
            ).fetchall()
        out: list[TelemetryEvent] = []
        for row in rows:
            payload = json.loads(row["payload"])
            out.append(TelemetryEvent.from_row(str(row["event"]), str(row["timestamp"]), payload))
        return out

    def fetch_session(self, session_id: str) -> list[TelemetryEvent]:
        with connection_lock(self._conn):
            rows = self._conn.execute(
                """
                SELECT event, timestamp, payload
                FROM telemetry_events
                WHERE json_extract(payload, '$.session_id') = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        out: list[TelemetryEvent] = []
        for row in rows:
            payload = json.loads(row["payload"])
            out.append(TelemetryEvent.from_row(str(row["event"]), str(row["timestamp"]), payload))
        return out

    def count(self) -> int:
        with connection_lock(self._conn):
            row = self._conn.execute("SELECT COUNT(*) AS n FROM telemetry_events").fetchone()
        return int(row["n"]) if row else 0
