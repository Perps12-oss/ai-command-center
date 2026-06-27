"""
Snapshot Service - Phase 1 Implementation

State snapshot management for checkpoint, restore, and undo.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ai_command_center.core.snapshot.snapshot import (
    StateSnapshot,
    SNAPSHOT_SCHEMA_VERSION,
    validate_snapshot_type,
)
from ai_command_center.core.event_bus import (
    Event,
    EVENT_SNAPSHOT_CREATED,
    EVENT_SNAPSHOT_RESTORED,
)


class SnapshotService:
    """
    State snapshot management.
    
    Responsibilities:
    - Create snapshots (checkpoint, manual, auto)
    - Restore snapshots
    - List snapshots
    - Event publishing for snapshot operations
    """

    def __init__(self, conn: sqlite3.Connection, event_bus: Any) -> None:
        self._conn = conn
        self._event_bus = event_bus
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create snapshots table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                snapshot_type TEXT NOT NULL,
                entities TEXT,
                relationships TEXT,
                active_workspace_id TEXT,
                workspace_layouts TEXT,
                settings TEXT,
                created_at TEXT NOT NULL,
                description TEXT,
                schema_version INTEGER NOT NULL
            )
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_created 
            ON snapshots(created_at)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_type 
            ON snapshots(snapshot_type)
        """)
        
        self._conn.commit()

    def create(
        self,
        snapshot_type: str,
        entities: dict[UUID, dict[str, Any]],
        relationships: dict[UUID, dict[str, Any]],
        active_workspace_id: UUID | None = None,
        workspace_layouts: dict[UUID, dict[str, Any]] | None = None,
        settings: dict[str, Any] | None = None,
        description: str = "",
    ) -> StateSnapshot:
        """Create a state snapshot."""
        if not validate_snapshot_type(snapshot_type):
            raise ValueError(f"Invalid snapshot_type: {snapshot_type}")
        
        snapshot = StateSnapshot(
            id=uuid4(),
            snapshot_type=snapshot_type,
            entities=entities,
            relationships=relationships,
            active_workspace_id=active_workspace_id,
            workspace_layouts=workspace_layouts or {},
            settings=settings or {},
            created_at=datetime.utcnow(),
            description=description,
            schema_version=SNAPSHOT_SCHEMA_VERSION,
        )
        
        self._conn.execute(
            """
            INSERT INTO snapshots (
                id, snapshot_type, entities, relationships, active_workspace_id,
                workspace_layouts, settings, created_at, description, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(snapshot.id),
                snapshot.snapshot_type,
                json.dumps(snapshot.entities),
                json.dumps(snapshot.relationships),
                str(snapshot.active_workspace_id) if snapshot.active_workspace_id else None,
                json.dumps(snapshot.workspace_layouts),
                json.dumps(snapshot.settings),
                snapshot.created_at.isoformat(),
                snapshot.description,
                snapshot.schema_version,
            ),
        )
        self._conn.commit()
        
        # Publish event
        self._event_bus.publish(
            EVENT_SNAPSHOT_CREATED,
            {
                "snapshot_id": str(snapshot.id),
                "snapshot_type": snapshot.snapshot_type,
                "description": snapshot.description,
            },
            source="snapshot_service",
        )
        
        return snapshot

    def get(self, snapshot_id: UUID) -> StateSnapshot | None:
        """Get snapshot by ID."""
        row = self._conn.execute(
            "SELECT * FROM snapshots WHERE id = ?",
            (str(snapshot_id),)
        ).fetchone()
        
        if row is None:
            return None
        
        return self._row_to_snapshot(row)

    def get_recent(self, limit: int = 10) -> list[StateSnapshot]:
        """Get recent snapshots."""
        rows = self._conn.execute(
            """
            SELECT * FROM snapshots 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        return [self._row_to_snapshot(row) for row in rows]

    def get_by_type(self, snapshot_type: str, limit: int = 10) -> list[StateSnapshot]:
        """Get snapshots by type."""
        rows = self._conn.execute(
            """
            SELECT * FROM snapshots 
            WHERE snapshot_type = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (snapshot_type, limit)
        ).fetchall()
        
        return [self._row_to_snapshot(row) for row in rows]

    def restore(self, snapshot_id: UUID) -> StateSnapshot | None:
        """
        Restore a snapshot.
        
        This is a placeholder - actual restore logic would apply the snapshot
        data to the relevant repositories and services.
        """
        snapshot = self.get(snapshot_id)
        if snapshot is None:
            return None
        
        # Placeholder: restore logic would be implemented by relevant services
        # For now, we just publish the event
        self._event_bus.publish(
            EVENT_SNAPSHOT_RESTORED,
            {
                "snapshot_id": str(snapshot.id),
                "snapshot_type": snapshot.snapshot_type,
            },
            source="snapshot_service",
        )
        
        return snapshot

    def delete(self, snapshot_id: UUID) -> bool:
        """Delete a snapshot."""
        cursor = self._conn.execute(
            "DELETE FROM snapshots WHERE id = ?",
            (str(snapshot_id),)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_old_snapshots(self, days: int = 30) -> int:
        """Delete snapshots older than specified days."""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cursor = self._conn.execute(
            "DELETE FROM snapshots WHERE created_at < ?",
            (cutoff_date.isoformat(),)
        )
        self._conn.commit()
        return cursor.rowcount

    def list_all(self) -> list[StateSnapshot]:
        """List all snapshots."""
        rows = self._conn.execute(
            "SELECT * FROM snapshots ORDER BY created_at DESC"
        ).fetchall()
        
        return [self._row_to_snapshot(row) for row in rows]

    def _row_to_snapshot(self, row: sqlite3.Row) -> StateSnapshot:
        """Convert database row to StateSnapshot."""
        return StateSnapshot(
            id=UUID(row["id"]),
            snapshot_type=row["snapshot_type"],
            entities={UUID(k): v for k, v in json.loads(row["entities"] or "{}").items()},
            relationships={UUID(k): v for k, v in json.loads(row["relationships"] or "{}").items()},
            active_workspace_id=UUID(row["active_workspace_id"]) if row["active_workspace_id"] else None,
            workspace_layouts={UUID(k): v for k, v in json.loads(row["workspace_layouts"] or "{}").items()},
            settings=json.loads(row["settings"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
            description=row["description"] or "",
            schema_version=row["schema_version"],
        )
