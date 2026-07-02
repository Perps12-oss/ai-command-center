"""
Timeline Repository - Phase 1 Implementation

Repository for timeline events following the frozen TimelineEvent contract.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from uuid import UUID

from ai_command_center.core.timeline.timeline_event import (
    TimelineEvent,
)


class TimelineRepository:
    """
    Repository for timeline events.
    
    Timeline provides universal event storage for audit, undo, analytics, and debugging.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create timeline_events table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS timeline_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                entity_id TEXT,
                entity_type TEXT,
                payload TEXT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                reversible BOOLEAN NOT NULL DEFAULT 0,
                undo_data TEXT,
                schema_version INTEGER NOT NULL
            )
        """)
        
        # Create indexes for time-series queries
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_timestamp 
            ON timeline_events(timestamp)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_event_type 
            ON timeline_events(event_type)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_entity 
            ON timeline_events(entity_id)
        """)
        
        self._conn.commit()

    def create(self, event: TimelineEvent) -> TimelineEvent:
        """Create a new timeline event."""
        self._conn.execute(
            """
            INSERT INTO timeline_events (
                id, event_type, entity_id, entity_type, payload, timestamp,
                user_id, reversible, undo_data, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.id),
                event.event_type,
                str(event.entity_id) if event.entity_id else None,
                event.entity_type,
                json.dumps(event.payload),
                event.timestamp.isoformat(),
                event.user_id,
                event.reversible,
                json.dumps(event.undo_data) if event.undo_data else None,
                event.schema_version,
            ),
        )
        self._conn.commit()
        return event

    def get(self, event_id: UUID) -> TimelineEvent | None:
        """Get timeline event by ID."""
        row = self._conn.execute(
            "SELECT * FROM timeline_events WHERE id = ?",
            (str(event_id),)
        ).fetchone()
        
        if row is None:
            return None
        
        return self._row_to_timeline_event(row)

    def get_by_entity(self, entity_id: UUID, limit: int = 100) -> list[TimelineEvent]:
        """Get timeline events for a specific entity."""
        rows = self._conn.execute(
            """
            SELECT * FROM timeline_events 
            WHERE entity_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (str(entity_id), limit)
        ).fetchall()
        
        return [self._row_to_timeline_event(row) for row in rows]

    def get_by_type(self, event_type: str, limit: int = 100) -> list[TimelineEvent]:
        """Get timeline events by event type."""
        rows = self._conn.execute(
            """
            SELECT * FROM timeline_events 
            WHERE event_type = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (event_type, limit)
        ).fetchall()
        
        return [self._row_to_timeline_event(row) for row in rows]

    def get_recent(self, limit: int = 50) -> list[TimelineEvent]:
        """Get recent timeline events."""
        rows = self._conn.execute(
            """
            SELECT * FROM timeline_events 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        return [self._row_to_timeline_event(row) for row in rows]

    def get_reversible(self, limit: int = 50) -> list[TimelineEvent]:
        """Get reversible timeline events (for undo)."""
        rows = self._conn.execute(
            """
            SELECT * FROM timeline_events 
            WHERE reversible = 1 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        return [self._row_to_timeline_event(row) for row in rows]

    def delete(self, event_id: UUID) -> bool:
        """Delete a timeline event by ID."""
        cursor = self._conn.execute(
            "DELETE FROM timeline_events WHERE id = ?",
            (str(event_id),)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_old_events(self, before_date: datetime) -> int:
        """Delete timeline events older than a given date."""
        cursor = self._conn.execute(
            "DELETE FROM timeline_events WHERE timestamp < ?",
            (before_date.isoformat(),)
        )
        self._conn.commit()
        return cursor.rowcount

    def list_all(self) -> list[TimelineEvent]:
        """List all timeline events."""
        rows = self._conn.execute(
            "SELECT * FROM timeline_events ORDER BY timestamp DESC"
        ).fetchall()
        
        return [self._row_to_timeline_event(row) for row in rows]

    def _row_to_timeline_event(self, row: sqlite3.Row) -> TimelineEvent:
        """Convert database row to TimelineEvent."""
        return TimelineEvent(
            id=UUID(row["id"]),
            event_type=row["event_type"],
            entity_id=UUID(row["entity_id"]) if row["entity_id"] else None,
            entity_type=row["entity_type"],
            payload=json.loads(row["payload"] or "{}"),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            user_id=row["user_id"],
            reversible=bool(row["reversible"]),
            undo_data=json.loads(row["undo_data"]) if row["undo_data"] else None,
            schema_version=row["schema_version"],
        )
