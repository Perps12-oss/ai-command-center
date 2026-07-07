"""Persistence for artifact records."""

from __future__ import annotations

import sqlite3
import time
import uuid

from ai_command_center.db.connection_lock import connection_lock
from ai_command_center.domain.artifact import Artifact, ArtifactType


class ArtifactRepository:
    """Owns artifacts table access."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = connection_lock(conn)

    def create(
        self,
        *,
        kind: ArtifactType | str,
        label: str,
        size_bytes: int = 0,
        content_ref: str = "",
        execution_id: str = "",
        mime_type: str = "",
        artifact_id: str = "",
    ) -> Artifact:
        resolved_id = artifact_id.strip() or uuid.uuid4().hex
        now = time.time()
        kind_value = ArtifactType.coerce(kind).value
        with self._lock:
            self._conn.execute(
                "INSERT INTO artifacts "
                "(artifact_id, kind, label, size_bytes, content_ref, execution_id, "
                "mime_type, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    resolved_id,
                    kind_value,
                    label,
                    int(size_bytes),
                    content_ref,
                    execution_id,
                    mime_type,
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return Artifact(
            artifact_id=resolved_id,
            kind=ArtifactType.coerce(kind_value),
            label=label,
            size_bytes=int(size_bytes),
            content_ref=content_ref,
            execution_id=execution_id,
            mime_type=mime_type,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        artifact_id: str,
        *,
        label: str | None = None,
        size_bytes: int | None = None,
        content_ref: str | None = None,
        mime_type: str | None = None,
    ) -> Artifact | None:
        existing = self.get(artifact_id)
        if existing is None:
            return None
        updated = Artifact(
            artifact_id=existing.artifact_id,
            kind=existing.kind,
            label=existing.label if label is None else label,
            size_bytes=existing.size_bytes if size_bytes is None else int(size_bytes),
            content_ref=existing.content_ref if content_ref is None else content_ref,
            execution_id=existing.execution_id,
            mime_type=existing.mime_type if mime_type is None else mime_type,
            created_at=existing.created_at,
            updated_at=time.time(),
        )
        with self._lock:
            self._conn.execute(
                "UPDATE artifacts SET kind = ?, label = ?, size_bytes = ?, content_ref = ?, "
                "execution_id = ?, mime_type = ?, created_at = ?, updated_at = ? "
                "WHERE artifact_id = ?",
                (
                    updated.kind.value,
                    updated.label,
                    updated.size_bytes,
                    updated.content_ref,
                    updated.execution_id,
                    updated.mime_type,
                    updated.created_at,
                    updated.updated_at,
                    updated.artifact_id,
                ),
            )
            self._conn.commit()
        return updated

    def get(self, artifact_id: str) -> Artifact | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT artifact_id, kind, label, size_bytes, content_ref, execution_id, "
                "mime_type, created_at, updated_at "
                "FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_artifact(row)

    def list_by_execution(self, execution_id: str, *, limit: int = 50) -> list[Artifact]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT artifact_id, kind, label, size_bytes, content_ref, execution_id, "
                "mime_type, created_at, updated_at "
                "FROM artifacts WHERE execution_id = ? "
                "ORDER BY created_at ASC LIMIT ?",
                (execution_id, limit),
            ).fetchall()
        return [self._row_to_artifact(row) for row in rows]

    def list_recent(self, *, limit: int = 50) -> list[Artifact]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT artifact_id, kind, label, size_bytes, content_ref, execution_id, "
                "mime_type, created_at, updated_at "
                "FROM artifacts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_artifact(row) for row in reversed(rows)]

    @staticmethod
    def _row_to_artifact(row: sqlite3.Row | tuple) -> Artifact:
        if isinstance(row, sqlite3.Row):
            return Artifact(
                artifact_id=str(row["artifact_id"]),
                kind=ArtifactType.coerce(str(row["kind"])),
                label=str(row["label"]),
                size_bytes=int(row["size_bytes"]),
                content_ref=str(row["content_ref"]),
                execution_id=str(row["execution_id"]),
                mime_type=str(row["mime_type"]),
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
            )
        (
            artifact_id,
            kind,
            label,
            size_bytes,
            content_ref,
            execution_id,
            mime_type,
            created_at,
            updated_at,
        ) = row
        return Artifact(
            artifact_id=str(artifact_id),
            kind=ArtifactType.coerce(str(kind)),
            label=str(label),
            size_bytes=int(size_bytes),
            content_ref=str(content_ref),
            execution_id=str(execution_id),
            mime_type=str(mime_type),
            created_at=float(created_at),
            updated_at=float(updated_at),
        )


__all__ = ["ArtifactRepository"]
