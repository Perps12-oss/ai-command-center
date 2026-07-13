"""WorkspaceRegistry — manages the set of federated workspace descriptors.

Responsibilities:
- Register / unregister workspaces.
- Persist registry to SQLite (separate table from mutation_journal).
- Provide the list of registered workspaces to FederatedWorldModel.

Architecture:
- No EventBus dependency. Pure data store.
- FederationService owns the EventBus integration.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ai_command_center.domain.federation import WorkspaceDescriptor, WorkspaceRole


class WorkspaceRegistry:
    """SQLite-backed registry of federated workspaces."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS federation_workspaces (
                workspace_id  TEXT PRIMARY KEY,
                name          TEXT NOT NULL DEFAULT '',
                role          TEXT NOT NULL DEFAULT 'read_only',
                db_path       TEXT NOT NULL DEFAULT '',
                tags_json     TEXT NOT NULL DEFAULT '[]',
                registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_fw_role ON federation_workspaces(role);
            """
        )
        self._conn.commit()

    def register(self, workspace: WorkspaceDescriptor) -> None:
        self._conn.execute(
            """
            INSERT INTO federation_workspaces
                (workspace_id, name, role, db_path, tags_json, registered_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                name          = excluded.name,
                role          = excluded.role,
                db_path       = excluded.db_path,
                tags_json     = excluded.tags_json
            """,
            (
                workspace.workspace_id,
                workspace.name,
                workspace.role.value,
                workspace.db_path,
                json.dumps(list(workspace.tags)),
                workspace.registered_at.isoformat(),
            ),
        )
        self._conn.commit()

    def unregister(self, workspace_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM federation_workspaces WHERE workspace_id = ?", (workspace_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get(self, workspace_id: str) -> WorkspaceDescriptor | None:
        row = self._conn.execute(
            "SELECT * FROM federation_workspaces WHERE workspace_id = ?", (workspace_id,)
        ).fetchone()
        return _row_to_descriptor(row) if row else None

    def list_all(self) -> list[WorkspaceDescriptor]:
        rows = self._conn.execute(
            "SELECT * FROM federation_workspaces ORDER BY registered_at ASC"
        ).fetchall()
        return [_row_to_descriptor(r) for r in rows]

    def list_by_role(self, role: WorkspaceRole) -> list[WorkspaceDescriptor]:
        rows = self._conn.execute(
            "SELECT * FROM federation_workspaces WHERE role = ? ORDER BY registered_at ASC",
            (role.value,),
        ).fetchall()
        return [_row_to_descriptor(r) for r in rows]


def _row_to_descriptor(row: sqlite3.Row) -> WorkspaceDescriptor:
    tags_raw: Any = json.loads(row["tags_json"] or "[]")
    tags = tuple(str(t) for t in tags_raw) if isinstance(tags_raw, list) else ()
    return WorkspaceDescriptor(
        workspace_id=str(row["workspace_id"]),
        name=str(row["name"] or ""),
        role=WorkspaceRole(str(row["role"])),
        db_path=str(row["db_path"] or ""),
        tags=tags,
    )
