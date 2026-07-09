"""Explicit memory graph — SQLite entity/relationship store (Phase 4E).

.. deprecated::
    Import ``MemoryRepository`` from ``ai_command_center.repositories`` instead.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemoryNode:
    id: str
    label: str
    kind: str
    content: str
    tier: str


class MemoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = threading.Lock()

    def remember(
        self,
        *,
        label: str,
        content: str,
        kind: str = "entity",
        tier: str = "mid",
        related_to: str | None = None,
        relation: str = "relates_to",
        workspace_id: str = "",
        entity_id: str = "",
    ) -> str:
        node_id = uuid.uuid4().hex
        now = time.time()
        with self._lock:
            try:
                self._remember_once(
                    node_id=node_id,
                    label=label,
                    content=content,
                    kind=kind,
                    tier=tier,
                    now=now,
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    related_to=related_to,
                    relation=relation,
                )
            except sqlite3.DatabaseError as exc:
                if "cannot start a transaction within a transaction" not in str(exc):
                    raise
                self._conn.rollback()
                self._remember_once(
                    node_id=node_id,
                    label=label,
                    content=content,
                    kind=kind,
                    tier=tier,
                    now=now,
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    related_to=related_to,
                    relation=relation,
                )
            self._conn.commit()
        return node_id

    def _remember_once(
        self,
        *,
        node_id: str,
        label: str,
        content: str,
        kind: str,
        tier: str,
        now: float,
        workspace_id: str,
        entity_id: str,
        related_to: str | None,
        relation: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO memory_nodes (
                id, label, kind, content, tier, created_at, workspace_id, entity_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                label,
                kind,
                content,
                tier,
                now,
                workspace_id.strip(),
                entity_id.strip(),
            ),
        )
        if related_to:
            self._conn.execute(
                """
                INSERT INTO memory_edges (source_id, target_id, relation, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (node_id, related_to, relation, now),
            )

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        workspace_id: str = "",
        entity_id: str = "",
        global_search: bool = False,
    ) -> list[MemoryNode]:
        pattern = f"%{query.strip()}%"
        if global_search:
            rows = self._conn.execute(
                """
                SELECT id, label, kind, content, tier
                FROM memory_nodes
                WHERE label LIKE ? OR content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            ).fetchall()
        else:
            ws = workspace_id.strip()
            ent = entity_id.strip()
            if not ws:
                return []
            if ent:
                rows = self._conn.execute(
                    """
                    SELECT id, label, kind, content, tier
                    FROM memory_nodes
                    WHERE workspace_id = ? AND entity_id = ?
                      AND (label LIKE ? OR content LIKE ?)
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (ws, ent, pattern, pattern, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT id, label, kind, content, tier
                    FROM memory_nodes
                    WHERE workspace_id = ? AND (label LIKE ? OR content LIKE ?)
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (ws, pattern, pattern, limit),
                ).fetchall()
        return [
            MemoryNode(
                id=str(r["id"]),
                label=str(r["label"]),
                kind=str(r["kind"]),
                content=str(r["content"]),
                tier=str(r["tier"]),
            )
            for r in rows
        ]

    def get(self, node_id: str) -> MemoryNode | None:
        row = self._conn.execute(
            "SELECT id, label, kind, content, tier FROM memory_nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if row is None:
            return None
        return MemoryNode(
            id=str(row["id"]),
            label=str(row["label"]),
            kind=str(row["kind"]),
            content=str(row["content"]),
            tier=str(row["tier"]),
        )

    def delete(self, node_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM memory_nodes WHERE id = ?",
            (node_id,),
        )
        self._conn.execute(
            "DELETE FROM memory_edges WHERE source_id = ? OR target_id = ?",
            (node_id, node_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0
