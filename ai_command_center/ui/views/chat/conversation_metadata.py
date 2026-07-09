"""ConversationMetadata — domain projection for the conversation list.

Reference: Open WebUI conversation list IA (pinned, recent, folders, tags).

This dataclass is UI-layer only and carries no persistence logic.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ConversationMetadata:
    """Lightweight projection of a persisted conversation entry.

    Fields
    ──────
    session_id    — opaque session identifier from SessionStore
    title         — display title (derived from first user message)
    provider_badge— short provider label: "ollama", "openai", "local", etc.
    last_activity — unix timestamp of last message (0 = unknown)
    pinned        — user has pinned this conversation to the top
    archived      — conversation is in the archive folder
    folder        — folder path (empty string = root / unfoldered)
    tags          — user-assigned tags
    unread        — number of unread messages (0 = none)
    message_count — total messages in the conversation
    """

    session_id: str = ""
    title: str = "New Chat"
    provider_badge: str = ""
    last_activity: float = field(default_factory=time.time)
    pinned: bool = False
    archived: bool = False
    folder: str = ""
    tags: tuple[str, ...] = ()
    unread: int = 0
    message_count: int = 0
    preview: str = ""

    def display_time(self) -> str:
        """Human-readable relative time for the list cell."""
        if not self.last_activity:
            return ""
        delta = time.time() - self.last_activity
        if delta < 60:
            return "now"
        if delta < 86400:
            return time.strftime("%I:%M %p", time.localtime(self.last_activity)).lstrip("0")
        if delta < 604800:
            return time.strftime("%a", time.localtime(self.last_activity))
        return time.strftime("%b %d", time.localtime(self.last_activity))

    def short_title(self, max_len: int = 38) -> str:
        t = self.title or "New Chat"
        return (t[:max_len - 1] + "…") if len(t) > max_len else t

    def preview_text(self, max_len: int = 42) -> str:
        text = (self.preview or self.title or "").strip()
        if not text:
            return "No messages yet"
        return (text[:max_len - 1] + "…") if len(text) > max_len else text

    def date_bucket(self) -> str:
        """Return Today / Yesterday / Previous 7 Days / Older."""
        if not self.last_activity:
            return "Older"
        now = time.time()
        delta = now - self.last_activity
        if delta < 86400:
            local = time.localtime(self.last_activity)
            today = time.localtime(now)
            if local.tm_yday == today.tm_yday and local.tm_year == today.tm_year:
                return "Today"
        if delta < 172800:
            return "Yesterday"
        if delta < 604800:
            return "Previous 7 Days"
        return "Older"
