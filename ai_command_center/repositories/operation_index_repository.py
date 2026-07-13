"""Repository for operation_index and operation_archive tables."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from ai_command_center.domain.operation_snapshot import OperationSnapshot


class OperationIndexRepository:
    """Owns operation_index and operation_archive table access.

    OperationIndexerService is the only writer.
    UI reads via OperationIndexerService (EventBus request/result pattern).
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS operation_index (
                correlation_id TEXT PRIMARY KEY,
                goal_id        TEXT NOT NULL DEFAULT '',
                goal_title     TEXT NOT NULL DEFAULT '',
                goal_status    TEXT NOT NULL DEFAULT 'unknown',
                goal_priority  TEXT NOT NULL DEFAULT 'normal',
                started_at     REAL,
                completed_at   REAL,
                agent_ids      TEXT NOT NULL DEFAULT '[]',
                execution_ids  TEXT NOT NULL DEFAULT '[]',
                tags           TEXT NOT NULL DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS idx_op_index_status
                ON operation_index(goal_status);
            CREATE INDEX IF NOT EXISTS idx_op_index_started
                ON operation_index(started_at DESC);

            CREATE TABLE IF NOT EXISTS operation_archive (
                correlation_id TEXT PRIMARY KEY,
                frozen_at      REAL NOT NULL,
                snapshot_json  TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def upsert(self, snapshot: OperationSnapshot) -> None:
        self._conn.execute(
            """
            INSERT INTO operation_index (
                correlation_id, goal_id, goal_title, goal_status, goal_priority,
                started_at, completed_at, agent_ids, execution_ids, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(correlation_id) DO UPDATE SET
                goal_id       = excluded.goal_id,
                goal_title    = excluded.goal_title,
                goal_status   = excluded.goal_status,
                goal_priority = excluded.goal_priority,
                started_at    = COALESCE(excluded.started_at, operation_index.started_at),
                completed_at  = excluded.completed_at,
                agent_ids     = excluded.agent_ids,
                execution_ids = excluded.execution_ids,
                tags          = excluded.tags
            """,
            (
                snapshot.correlation_id,
                snapshot.goal_id,
                snapshot.goal_title,
                snapshot.goal_status,
                snapshot.goal_priority,
                snapshot.started_at or None,
                snapshot.completed_at or None,
                json.dumps(list(snapshot.agent_ids)),
                json.dumps(list(snapshot.execution_ids)),
                json.dumps(list(snapshot.tags)),
            ),
        )
        self._conn.commit()

    def get(self, correlation_id: str) -> OperationSnapshot | None:
        row = self._conn.execute(
            "SELECT * FROM operation_index WHERE correlation_id = ?",
            (correlation_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_snapshot(row)

    def list_recent(self, *, limit: int = 50) -> list[OperationSnapshot]:
        rows = self._conn.execute(
            "SELECT * FROM operation_index ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_snapshot(row) for row in rows]

    def list_active(self) -> list[OperationSnapshot]:
        rows = self._conn.execute(
            "SELECT * FROM operation_index"
            " WHERE goal_status IN ('active', 'queued')"
            " ORDER BY started_at ASC"
        ).fetchall()
        return [_row_to_snapshot(row) for row in rows]

    def archive(self, snapshot: OperationSnapshot) -> None:
        """Freeze a snapshot immutably to operation_archive."""
        self._conn.execute(
            """
            INSERT INTO operation_archive (correlation_id, frozen_at, snapshot_json)
            VALUES (?, ?, ?)
            ON CONFLICT(correlation_id) DO NOTHING
            """,
            (snapshot.correlation_id, time.time(), json.dumps(snapshot.to_dict())),
        )
        self._conn.commit()

    def get_archive(self, correlation_id: str) -> OperationSnapshot | None:
        row = self._conn.execute(
            "SELECT snapshot_json FROM operation_archive WHERE correlation_id = ?",
            (correlation_id,),
        ).fetchone()
        if row is None:
            return None
        data: dict[str, Any] = json.loads(row[0])
        return OperationSnapshot.from_dict(data)


def _row_to_snapshot(row: sqlite3.Row) -> OperationSnapshot:
    return OperationSnapshot(
        correlation_id=str(row["correlation_id"]),
        goal_id=str(row["goal_id"] or ""),
        goal_title=str(row["goal_title"] or ""),
        goal_status=str(row["goal_status"] or "unknown"),
        goal_priority=str(row["goal_priority"] or "normal"),
        started_at=float(row["started_at"] or 0.0),
        completed_at=float(row["completed_at"] or 0.0),
        agent_ids=tuple(json.loads(row["agent_ids"] or "[]")),
        execution_ids=tuple(json.loads(row["execution_ids"] or "[]")),
        tags=tuple(json.loads(row["tags"] or "[]")),
    )
