"""Canonical conversation contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    role: str
    content: str
    created_at: float | None = None


@dataclass(frozen=True, slots=True)
class ConversationCatalogItem:
    """Rail projection of a persisted free-floating conversation (C6)."""

    conversation_id: str
    title: str = "New Chat"
    created_at: float = 0.0
    last_activity: float = 0.0
    message_count: int = 0
    model: str = ""


@dataclass(frozen=True, slots=True)
class Conversation:
    conversation_id: str
    title: str = ""
    messages: tuple[ConversationMessage, ...] = field(default_factory=tuple)
    updated_at: datetime = field(default_factory=datetime.utcnow)
