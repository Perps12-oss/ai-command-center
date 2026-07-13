"""Append-only persistence for execution timeline events (ACC UI PR 8)."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid

from ai_command_center.domain.execution_event import ExecutionEvent, _dict_to_pairs


class ExecutionEventRepository:
    """Owns execution_events table access."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ensure_table()

    def _ensure_table(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS execution_events (
                event_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL DEFAULT '',
                parent_event_id TEXT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT '',
                scope TEXT NOT NULL DEFAULT '',
                request_id TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL DEFAULT '{}',
                state_diff TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_execution_events_request
                ON execution_events(request_id);
            CREATE INDEX IF NOT EXISTS idx_execution_events_trace
                ON execution_events(trace_id);
            CREATE INDEX IF NOT EXISTS idx_execution_events_timestamp
                ON execution_events(timestamp);
            """
        )

    def append(self, event: ExecutionEvent) -> ExecutionEvent:
        event_id = event.event_id or uuid.uuid4().hex
        timestamp = event.timestamp or time.time()
        stored = ExecutionEvent(
            event_id=event_id,
            trace_id=event.trace_id,
            parent_event_id=event.parent_event_id,
            timestamp=timestamp,
            event_type=event.event_type,
            actor=event.actor,
            scope=event.scope,
            request_id=event.request_id,
            payload=event.payload,
            state_diff=event.state_diff,
        )
        self._conn.execute(
            """
            INSERT INTO execution_events (
                event_id, trace_id, parent_event_id, timestamp, event_type,
                actor, scope, request_id, payload, state_diff
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stored.event_id,
                stored.trace_id,
                stored.parent_event_id,
                stored.timestamp,
                stored.event_type,
                stored.actor,
                stored.scope,
                stored.request_id,
                json.dumps(dict(stored.payload)),
                json.dumps(dict(stored.state_diff)) if stored.state_diff is not None else None,
            ),
        )
        self._conn.commit()
        return stored

    def list_by_request(self, request_id: str, *, limit: int = 200) -> list[ExecutionEvent]:
        rows = self._conn.execute(
            """
            SELECT event_id, trace_id, parent_event_id, timestamp, event_type,
                   actor, scope, request_id, payload, state_diff
            FROM execution_events
            WHERE request_id = ?
            ORDER BY timestamp ASC, event_id ASC
            LIMIT ?
            """,
            (request_id, limit),
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def list_by_trace(self, trace_id: str, *, limit: int = 200) -> list[ExecutionEvent]:
        rows = self._conn.execute(
            """
            SELECT event_id, trace_id, parent_event_id, timestamp, event_type,
                   actor, scope, request_id, payload, state_diff
            FROM execution_events
            WHERE trace_id = ?
            ORDER BY timestamp ASC, event_id ASC
            LIMIT ?
            """,
            (trace_id, limit),
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def list_recent(self, *, limit: int = 50) -> list[ExecutionEvent]:
        rows = self._conn.execute(
            """
            SELECT event_id, trace_id, parent_event_id, timestamp, event_type,
                   actor, scope, request_id, payload, state_diff
            FROM execution_events
            ORDER BY timestamp DESC, event_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_event(row) for row in reversed(rows)]

    @staticmethod
    def _row_to_event(row: sqlite3.Row | tuple) -> ExecutionEvent:
        if isinstance(row, sqlite3.Row):
            payload_raw = row["payload"]
            diff_raw = row["state_diff"]
            parent = row["parent_event_id"]
            return ExecutionEvent(
                event_id=str(row["event_id"]),
                trace_id=str(row["trace_id"] or ""),
                parent_event_id=str(parent) if parent else None,
                timestamp=float(row["timestamp"] or 0.0),
                event_type=str(row["event_type"] or ""),
                actor=str(row["actor"] or ""),
                scope=str(row["scope"] or ""),
                request_id=str(row["request_id"] or ""),
                payload=_dict_to_pairs(json.loads(payload_raw) if payload_raw else {}),
                state_diff=(
                    _dict_to_pairs(json.loads(diff_raw))
                    if diff_raw
                    else None
                ),
            )
        (
            event_id,
            trace_id,
            parent_event_id,
            timestamp,
            event_type,
            actor,
            scope,
            request_id,
            payload_raw,
            state_diff_raw,
        ) = row
        return ExecutionEvent(
            event_id=str(event_id),
            trace_id=str(trace_id or ""),
            parent_event_id=str(parent_event_id) if parent_event_id else None,
            timestamp=float(timestamp or 0.0),
            event_type=str(event_type or ""),
            actor=str(actor or ""),
            scope=str(scope or ""),
            request_id=str(request_id or ""),
            payload=_dict_to_pairs(json.loads(payload_raw) if payload_raw else {}),
            state_diff=(
                _dict_to_pairs(json.loads(state_diff_raw))
                if state_diff_raw
                else None
            ),
        )
