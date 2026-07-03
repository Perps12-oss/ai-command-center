"""Single- and per-entity conversation persistence (Phase 3D + Track 9 C3).

.. deprecated::
    Import ``ConversationRepository`` from ``ai_command_center.repositories`` instead.
"""

from __future__ import annotations

import sqlite3
import time

from ai_command_center.domain.conversation import ConversationMessage

DEFAULT_CONVERSATION_ID = "default"
CONTEXT_HISTORY_LIMIT = 6


def entity_conversation_id(entity_type: str, entity_id: str) -> str:
    """Stable conversation key for a workspace entity chat session."""
    return f"entity:{entity_type}:{entity_id}"


class ConversationRepository:
    """Conversation rows keyed by id — default plus per-entity sessions."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def ensure_conversation(
        self,
        conversation_id: str,
        *,
        model: str = "",
        title: str = "Session",
    ) -> str:
        row = self._conn.execute(
            "SELECT id FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO conversations (id, title, model, created_at) VALUES (?, ?, ?, ?)",
                (conversation_id, title, model, time.time()),
            )
            self._conn.commit()
        elif model:
            self._conn.execute(
                "UPDATE conversations SET model = ? WHERE id = ?",
                (model, conversation_id),
            )
            self._conn.commit()
        return conversation_id

    def ensure_default(self, *, model: str = "") -> str:
        return self.ensure_conversation(DEFAULT_CONVERSATION_ID, model=model)

    def append_message(
        self,
        role: str,
        content: str,
        *,
        conversation_id: str | None = None,
    ) -> None:
        cid = conversation_id or DEFAULT_CONVERSATION_ID
        self.ensure_conversation(cid)
        self._conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (cid, role, content.strip(), time.time()),
        )
        self._conn.commit()

    def list_messages(
        self,
        conversation_id: str | None = None,
    ) -> list[ConversationMessage]:
        cid = conversation_id or DEFAULT_CONVERSATION_ID
        rows = self._conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (cid,),
        ).fetchall()
        return [
            ConversationMessage(
                role=str(r["role"]),
                content=str(r["content"]),
                created_at=float(r["created_at"]),
            )
            for r in rows
        ]

    def get_history_pairs(
        self,
        limit: int = CONTEXT_HISTORY_LIMIT,
        *,
        conversation_id: str | None = None,
    ) -> list[tuple[str, str]]:
        cid = conversation_id or DEFAULT_CONVERSATION_ID
        rows = self._conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (cid, limit),
        ).fetchall()
        return [(str(r["role"]), str(r["content"])) for r in reversed(rows)]

    def message_count(self, conversation_id: str | None = None) -> int:
        cid = conversation_id or DEFAULT_CONVERSATION_ID
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE conversation_id = ?",
            (cid,),
        ).fetchone()
        return int(row["c"]) if row else 0

    def clear_messages(self, conversation_id: str) -> None:
        """Remove all messages for a conversation row (row itself is kept)."""
        self.ensure_conversation(conversation_id)
        self._conn.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        self._conn.commit()
