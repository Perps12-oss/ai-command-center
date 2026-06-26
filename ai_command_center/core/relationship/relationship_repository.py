"""
Relationship Repository - Phase 1 Implementation

Repository for entity-to-entity relationships following the frozen Relationship contract.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ai_command_center.core.relationship.relationship import (
    Relationship,
    RelationshipType,
    RELATIONSHIP_SCHEMA_VERSION,
    validate_relationship_type,
)


class RelationshipRepository:
    """
    Repository for entity-to-entity relationships.
    
    Relationships are stored as first-class objects to enable graph queries,
    traversal, and relationship-level metadata.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create relationships table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for graph queries
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_source 
            ON relationships(source_id)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_target 
            ON relationships(target_id)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_type 
            ON relationships(relationship_type)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_source_target 
            ON relationships(source_id, target_id)
        """)
        
        self._conn.commit()

    def create(self, relationship: Relationship) -> Relationship:
        """Create a new relationship."""
        if not validate_relationship_type(relationship.relationship_type.value):
            raise ValueError(f"Invalid relationship_type: {relationship.relationship_type}")
        
        self._conn.execute(
            """
            INSERT INTO relationships (
                id, source_id, target_id, relationship_type, created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(relationship.id),
                str(relationship.source_id),
                str(relationship.target_id),
                relationship.relationship_type.value,
                relationship.created_at.isoformat(),
                json.dumps(relationship.metadata),
            ),
        )
        self._conn.commit()
        return relationship

    def get(self, relationship_id: UUID) -> Relationship | None:
        """Get relationship by ID."""
        row = self._conn.execute(
            "SELECT * FROM relationships WHERE id = ?",
            (str(relationship_id),)
        ).fetchone()
        
        if row is None:
            return None
        
        return self._row_to_relationship(row)

    def get_by_source(self, source_id: UUID) -> list[Relationship]:
        """Get all relationships where source_id is the source."""
        rows = self._conn.execute(
            "SELECT * FROM relationships WHERE source_id = ? ORDER BY created_at DESC",
            (str(source_id),)
        ).fetchall()
        
        return [self._row_to_relationship(row) for row in rows]

    def get_by_target(self, target_id: UUID) -> list[Relationship]:
        """Get all relationships where target_id is the target."""
        rows = self._conn.execute(
            "SELECT * FROM relationships WHERE target_id = ? ORDER BY created_at DESC",
            (str(target_id),)
        ).fetchall()
        
        return [self._row_to_relationship(row) for row in rows]

    def get_by_type(self, relationship_type: RelationshipType) -> list[Relationship]:
        """Get all relationships of a specific type."""
        rows = self._conn.execute(
            "SELECT * FROM relationships WHERE relationship_type = ? ORDER BY created_at DESC",
            (relationship_type.value,)
        ).fetchall()
        
        return [self._row_to_relationship(row) for row in rows]

    def get_between(self, source_id: UUID, target_id: UUID) -> list[Relationship]:
        """Get all relationships between two entities."""
        rows = self._conn.execute(
            """
            SELECT * FROM relationships 
            WHERE source_id = ? AND target_id = ? 
            ORDER BY created_at DESC
            """,
            (str(source_id), str(target_id))
        ).fetchall()
        
        return [self._row_to_relationship(row) for row in rows]

    def delete(self, relationship_id: UUID) -> bool:
        """Delete a relationship by ID."""
        cursor = self._conn.execute(
            "DELETE FROM relationships WHERE id = ?",
            (str(relationship_id),)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_between(self, source_id: UUID, target_id: UUID) -> int:
        """Delete all relationships between two entities."""
        cursor = self._conn.execute(
            "DELETE FROM relationships WHERE source_id = ? AND target_id = ?",
            (str(source_id), str(target_id))
        )
        self._conn.commit()
        return cursor.rowcount

    def list_all(self) -> list[Relationship]:
        """List all relationships."""
        rows = self._conn.execute(
            "SELECT * FROM relationships ORDER BY created_at DESC"
        ).fetchall()
        
        return [self._row_to_relationship(row) for row in rows]

    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        """Convert database row to Relationship."""
        return Relationship(
            id=UUID(row["id"]),
            source_id=UUID(row["source_id"]),
            target_id=UUID(row["target_id"]),
            relationship_type=RelationshipType(row["relationship_type"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"] or "{}"),
        )
