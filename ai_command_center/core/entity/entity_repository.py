"""
Entity Repository - Phase 1 Implementation

Universal CRUD for all entity types following the frozen Entity contract.
"""

from __future__ import annotations

import sqlite3
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ai_command_center.core.entity.entity import (
    Entity,
    ENTITY_SCHEMA_VERSION,
    validate_entity_type,
)


class EntityRepository:
    """
    Universal repository for all entity types.
    
    All entities (Workspace, Agent, Workflow, Prompt, Card, Project, File, etc.)
    are stored in a unified entities table with entity_type discriminator.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create entities table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                metadata TEXT,
                relationships TEXT,
                embedding_status TEXT DEFAULT 'none',
                embedding_vector BLOB
            )
        """)
        
        # Create indexes for common queries
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_type 
            ON entities(entity_type)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_created 
            ON entities(created_at)
        """)
        
        self._conn.commit()

    def create(self, entity: Entity) -> Entity:
        """Create a new entity."""
        if not validate_entity_type(entity.entity_type):
            raise ValueError(f"Invalid entity_type: {entity.entity_type}")
        
        self._conn.execute(
            """
            INSERT INTO entities (
                id, entity_type, title, description, created_at, updated_at,
                schema_version, metadata, relationships, embedding_status, embedding_vector
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(entity.id),
                entity.entity_type,
                entity.title,
                entity.description,
                entity.created_at.isoformat(),
                entity.updated_at.isoformat(),
                entity.schema_version,
                json.dumps(entity.metadata),
                json.dumps([str(r) for r in entity.relationships]),
                entity.embedding_status,
                entity.embedding_vector,
            ),
        )
        self._conn.commit()
        return entity

    def get(self, entity_id: UUID) -> Entity | None:
        """Get entity by ID."""
        row = self._conn.execute(
            "SELECT * FROM entities WHERE id = ?",
            (str(entity_id),)
        ).fetchone()
        
        if row is None:
            return None
        
        return self._row_to_entity(row)

    def get_by_type(self, entity_type: str) -> list[Entity]:
        """Get all entities of a specific type."""
        rows = self._conn.execute(
            "SELECT * FROM entities WHERE entity_type = ? ORDER BY created_at DESC",
            (entity_type,)
        ).fetchall()
        
        return [self._row_to_entity(row) for row in rows]

    def update(self, entity: Entity) -> Entity:
        """Update an existing entity."""
        self._conn.execute(
            """
            UPDATE entities SET
                title = ?,
                description = ?,
                updated_at = ?,
                schema_version = ?,
                metadata = ?,
                relationships = ?,
                embedding_status = ?,
                embedding_vector = ?
            WHERE id = ?
            """,
            (
                entity.title,
                entity.description,
                entity.updated_at.isoformat(),
                entity.schema_version,
                json.dumps(entity.metadata),
                json.dumps([str(r) for r in entity.relationships]),
                entity.embedding_status,
                entity.embedding_vector,
                str(entity.id),
            ),
        )
        self._conn.commit()
        return entity

    def delete(self, entity_id: UUID) -> bool:
        """Delete an entity by ID."""
        cursor = self._conn.execute(
            "DELETE FROM entities WHERE id = ?",
            (str(entity_id),)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def list_all(self) -> list[Entity]:
        """List all entities."""
        rows = self._conn.execute(
            "SELECT * FROM entities ORDER BY created_at DESC"
        ).fetchall()
        
        return [self._row_to_entity(row) for row in rows]

    def search(self, query: str, entity_type: str | None = None) -> list[Entity]:
        """Search entities by title or description."""
        if entity_type:
            rows = self._conn.execute(
                """
                SELECT * FROM entities 
                WHERE entity_type = ? 
                AND (title LIKE ? OR description LIKE ?)
                ORDER BY created_at DESC
                """,
                (entity_type, f"%{query}%", f"%{query}%")
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM entities 
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY created_at DESC
                """,
                (f"%{query}%", f"%{query}%")
            ).fetchall()
        
        return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert database row to Entity."""
        return Entity(
            id=UUID(row["id"]),
            entity_type=row["entity_type"],
            title=row["title"],
            description=row["description"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            schema_version=row["schema_version"],
            metadata=json.loads(row["metadata"] or "{}"),
            relationships=[UUID(r) for r in json.loads(row["relationships"] or "[]")],
            embedding_status=row["embedding_status"] or "none",
            embedding_vector=row["embedding_vector"],
        )
