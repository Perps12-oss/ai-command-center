"""SQLite persistence for artifact records (ACC UI Refurbishment PR 6)."""

from __future__ import annotations

import sqlite3
import time

from ai_command_center.domain.artifact import Artifact


class ArtifactRepository:
    """Owns artifacts table access."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, artifact: Artifact) -> Artifact:
        now = time.time()
        created = artifact.created_at or now
        updated = artifact.updated_at or now
        self._conn.execute(
            """
            INSERT INTO artifacts (
                artifact_id, kind, label, content, size_bytes, mime_type,
                request_id, workspace_id, entity_id, source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.artifact_id,
                artifact.normalized_kind(),
                artifact.label,
                artifact.content,
                artifact.size_bytes,
                artifact.mime_type,
                artifact.request_id,
                artifact.workspace_id,
                artifact.entity_id,
                artifact.source,
                created,
                updated,
            ),
        )
        self._conn.commit()
        return Artifact(
            artifact_id=artifact.artifact_id,
            kind=artifact.normalized_kind(),
            label=artifact.label,
            content=artifact.content,
            size_bytes=artifact.size_bytes,
            mime_type=artifact.mime_type,
            request_id=artifact.request_id,
            workspace_id=artifact.workspace_id,
            entity_id=artifact.entity_id,
            source=artifact.source,
            created_at=created,
            updated_at=updated,
        )

    def update(self, artifact: Artifact) -> Artifact | None:
        row = self._conn.execute(
            "SELECT artifact_id FROM artifacts WHERE artifact_id = ?",
            (artifact.artifact_id,),
        ).fetchone()
        if row is None:
            return None
        now = time.time()
        updated = artifact.updated_at or now
        self._conn.execute(
            """
            UPDATE artifacts
            SET kind = ?, label = ?, content = ?, size_bytes = ?, mime_type = ?,
                request_id = ?, workspace_id = ?, entity_id = ?, source = ?,
                updated_at = ?
            WHERE artifact_id = ?
            """,
            (
                artifact.normalized_kind(),
                artifact.label,
                artifact.content,
                artifact.size_bytes,
                artifact.mime_type,
                artifact.request_id,
                artifact.workspace_id,
                artifact.entity_id,
                artifact.source,
                updated,
                artifact.artifact_id,
            ),
        )
        self._conn.commit()
        return self.get(artifact.artifact_id)

    def get(self, artifact_id: str) -> Artifact | None:
        row = self._conn.execute(
            """
            SELECT artifact_id, kind, label, content, size_bytes, mime_type,
                   request_id, workspace_id, entity_id, source, created_at, updated_at
            FROM artifacts WHERE artifact_id = ?
            """,
            (artifact_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_artifact(row)

    def list_recent(self, *, limit: int = 50) -> list[Artifact]:
        rows = self._conn.execute(
            """
            SELECT artifact_id, kind, label, content, size_bytes, mime_type,
                   request_id, workspace_id, entity_id, source, created_at, updated_at
            FROM artifacts
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_artifact(row) for row in reversed(rows)]

    @staticmethod
    def _row_to_artifact(row: sqlite3.Row | tuple) -> Artifact:
        if isinstance(row, sqlite3.Row):
            return Artifact(
                artifact_id=str(row["artifact_id"]),
                kind=str(row["kind"]),
                label=str(row["label"]),
                content=str(row["content"] or ""),
                size_bytes=int(row["size_bytes"] or 0),
                mime_type=str(row["mime_type"] or ""),
                request_id=str(row["request_id"] or ""),
                workspace_id=str(row["workspace_id"] or ""),
                entity_id=str(row["entity_id"] or ""),
                source=str(row["source"] or ""),
                created_at=float(row["created_at"] or 0.0),
                updated_at=float(row["updated_at"] or 0.0),
            )
        (
            artifact_id,
            kind,
            label,
            content,
            size_bytes,
            mime_type,
            request_id,
            workspace_id,
            entity_id,
            source,
            created_at,
            updated_at,
        ) = row
        return Artifact(
            artifact_id=str(artifact_id),
            kind=str(kind),
            label=str(label),
            content=str(content or ""),
            size_bytes=int(size_bytes or 0),
            mime_type=str(mime_type or ""),
            request_id=str(request_id or ""),
            workspace_id=str(workspace_id or ""),
            entity_id=str(entity_id or ""),
            source=str(source or ""),
            created_at=float(created_at or 0.0),
            updated_at=float(updated_at or 0.0),
        )
