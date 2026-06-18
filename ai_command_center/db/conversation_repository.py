"""Single-session conversation persistence (Phase 3D)."""

from __future__ import annotations

import sqlite3
import time

DEFAULT_CONVERSATION_ID = "default"
CONTEXT_HISTORY_LIMIT = 6


class ConversationRepository:
    """One active conversation row — no multi-chat in Phase 3."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def ensure_default(self, *, model: str = "") -> str:
        row = self._conn.execute(
            "SELECT id FROM conversations WHERE id = ?",
            (DEFAULT_CONVERSATION_ID,),
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO conversations (id, title, model, created_at) VALUES (?, ?, ?, ?)",
                (DEFAULT_CONVERSATION_ID, "Session", model, time.time()),
            )
            self._conn.commit()
        elif model:
            self._conn.execute(
                "UPDATE conversations SET model = ? WHERE id = ?",
                (model, DEFAULT_CONVERSATION_ID),
            )
            self._conn.commit()
        return DEFAULT_CONVERSATION_ID

    def append_message(self, role: str, content: str) -> None:
        self.ensure_default()
        self._conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (DEFAULT_CONVERSATION_ID, role, content.strip(), time.time()),
        )
        self._conn.commit()

    def list_messages(self) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (DEFAULT_CONVERSATION_ID,),
        ).fetchall()
        return [
            {
                "role": str(r["role"]),
                "content": str(r["content"]),
                "created_at": float(r["created_at"]),
            }
            for r in rows
        ]

    def get_history_pairs(self, limit: int = CONTEXT_HISTORY_LIMIT) -> list[tuple[str, str]]:
        rows = self._conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (DEFAULT_CONVERSATION_ID, limit),
        ).fetchall()
        return [(str(r["role"]), str(r["content"])) for r in reversed(rows)]

    def message_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE conversation_id = ?",
            (DEFAULT_CONVERSATION_ID,),
        ).fetchone()
        return int(row["c"]) if row else 0
