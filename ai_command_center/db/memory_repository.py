"""Explicit memory graph — SQLite entity/relationship store (Phase 4E).

.. deprecated::
    Import ``MemoryRepository`` from ``ai_command_center.repositories`` instead.
"""

from __future__ import annotations

import sqlite3
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

    def remember(
        self,
        *,
        label: str,
        content: str,
        kind: str = "entity",
        tier: str = "mid",
        related_to: str | None = None,
        relation: str = "relates_to",
    ) -> str:
        node_id = uuid.uuid4().hex
        now = time.time()
        self._conn.execute(
            """
            INSERT INTO memory_nodes (id, label, kind, content, tier, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (node_id, label, kind, content, tier, now),
        )
        if related_to:
            self._conn.execute(
                """
                INSERT INTO memory_edges (source_id, target_id, relation, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (node_id, related_to, relation, now),
            )
        self._conn.commit()
        return node_id

    def search(self, query: str, *, limit: int = 5) -> list[MemoryNode]:
        pattern = f"%{query.strip()}%"
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
