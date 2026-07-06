"""Append-only persistence for execution runs."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid

from ai_command_center.domain.execution_run import ExecutionRun


class ExecutionRunRepository:
    """Owns execution_runs table access."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def append(
        self,
        *,
        request_id: str,
        source: str,
        snapshot: dict[str, object],
    ) -> ExecutionRun:
        run_id = uuid.uuid4().hex
        created_at = time.time()
        self._conn.execute(
            "INSERT INTO execution_runs (run_id, request_id, source, snapshot, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, request_id, source, json.dumps(snapshot), created_at),
        )
        self._conn.commit()
        return ExecutionRun(
            run_id=run_id,
            request_id=request_id,
            source=source,
            snapshot=dict(snapshot),
            created_at=created_at,
        )

    def list_by_request(self, request_id: str, *, limit: int = 50) -> list[ExecutionRun]:
        rows = self._conn.execute(
            "SELECT run_id, request_id, source, snapshot, created_at "
            "FROM execution_runs WHERE request_id = ? "
            "ORDER BY created_at ASC LIMIT ?",
            (request_id, limit),
        ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def list_recent(self, *, limit: int = 20) -> list[ExecutionRun]:
        rows = self._conn.execute(
            "SELECT run_id, request_id, source, snapshot, created_at "
            "FROM execution_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_run(row) for row in reversed(rows)]

    @staticmethod
    def _row_to_run(row: sqlite3.Row | tuple) -> ExecutionRun:
        if isinstance(row, sqlite3.Row):
            snapshot_raw = row["snapshot"]
            return ExecutionRun(
                run_id=str(row["run_id"]),
                request_id=str(row["request_id"]),
                source=str(row["source"]),
                snapshot=json.loads(snapshot_raw) if snapshot_raw else {},
                created_at=float(row["created_at"]),
            )
        run_id, request_id, source, snapshot_raw, created_at = row
        return ExecutionRun(
            run_id=str(run_id),
            request_id=str(request_id),
            source=str(source),
            snapshot=json.loads(snapshot_raw) if snapshot_raw else {},
            created_at=float(created_at),
        )
