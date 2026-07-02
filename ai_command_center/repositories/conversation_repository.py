"""Conversation repository wrapper for the new architecture package."""

from __future__ import annotations

import sqlite3

from ai_command_center.db.conversation_repository import (
    CONTEXT_HISTORY_LIMIT,
    ConversationRepository as DbConversationRepository,
)


class ConversationRepository(DbConversationRepository):
    """Compatibility wrapper that exposes the repository contract via the new package."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(conn)


__all__ = ["ConversationRepository", "CONTEXT_HISTORY_LIMIT"]
