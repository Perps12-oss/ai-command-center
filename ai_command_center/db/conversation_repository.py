"""Single- and per-entity conversation persistence (Phase 3D + Track 9 C3).

.. deprecated::
    Import ``ConversationRepository`` from ``ai_command_center.repositories`` instead.
"""

from __future__ import annotations

import sqlite3
import time
import uuid

from ai_command_center.db.conn_sync import connection_lock
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
        with connection_lock(self._conn):
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

    def create_conversation(
        self,
        *,
        title: str = "New Chat",
        model: str = "",
    ) -> str:
        """Insert a new free-floating conversation and return its id (C5)."""
        cid = uuid.uuid4().hex
        with connection_lock(self._conn):
            self._conn.execute(
                "INSERT INTO conversations (id, title, model, created_at) VALUES (?, ?, ?, ?)",
                (cid, title[:80] or "New Chat", model, time.time()),
            )
            self._conn.commit()
        return cid

    def list_conversations(self, *, limit: int = 50) -> list[dict[str, object]]:
        """List free-floating conversations for the chat rail (excludes entity:*)."""
        with connection_lock(self._conn):
            rows = self._conn.execute(
                """
                SELECT
                    c.id AS id,
                    c.title AS title,
                    c.model AS model,
                    c.created_at AS created_at,
                    COALESCE(MAX(m.created_at), c.created_at) AS last_activity,
                    COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.id NOT LIKE \'entity:%\'
                GROUP BY c.id
                ORDER BY last_activity DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        return [
            {
                "conversation_id": str(r["id"]),
                "title": str(r["title"] or "New Chat"),
                "model": str(r["model"] or ""),
                "created_at": float(r["created_at"] or 0.0),
                "last_activity": float(r["last_activity"] or 0.0),
                "message_count": int(r["message_count"] or 0),
            }
            for r in rows
        ]

    def update_title(self, conversation_id: str, title: str) -> None:
        clean = (title or "").strip()[:80] or "New Chat"
        with connection_lock(self._conn):
            self._conn.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (clean, conversation_id),
            )
            self._conn.commit()

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and its messages (CASCADE)."""
        if conversation_id == DEFAULT_CONVERSATION_ID:
            self.clear_messages(conversation_id)
            return
        with connection_lock(self._conn):
            self._conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            self._conn.commit()

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
        with connection_lock(self._conn):
            row = self._conn.execute(
                "SELECT id, title FROM conversations WHERE id = ?",
                (cid,),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO conversations (id, title, model, created_at) VALUES (?, ?, ?, ?)",
                    (cid, "Session", "", time.time()),
                )
                title = "Session"
            else:
                title = str(row["title"] or "")
            self._conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (cid, role, content.strip(), time.time()),
            )
            if role == "user" and title in ("", "Session", "New Chat", "Workspace", "Entity chat"):
                derived = content.strip().splitlines()[0][:60] if content.strip() else title
                if derived:
                    self._conn.execute(
                        "UPDATE conversations SET title = ? WHERE id = ?",
                        (derived, cid),
                    )
            self._conn.commit()

    def list_messages(
        self,
        conversation_id: str | None = None,
    ) -> list[ConversationMessage]:
        cid = conversation_id or DEFAULT_CONVERSATION_ID
        with connection_lock(self._conn):
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
        with connection_lock(self._conn):
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
        with connection_lock(self._conn):
            row = self._conn.execute(
                "SELECT COUNT(*) AS c FROM messages WHERE conversation_id = ?",
                (cid,),
            ).fetchone()
        return int(row["c"]) if row else 0

    def clear_messages(self, conversation_id: str) -> None:
        """Remove all messages for a conversation row (row itself is kept)."""
        with connection_lock(self._conn):
            row = self._conn.execute(
                "SELECT id FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO conversations (id, title, model, created_at) VALUES (?, ?, ?, ?)",
                    (conversation_id, "Session", "", time.time()),
                )
            self._conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            self._conn.commit()
