"""Domain snapshot: typed projection of Chat Session state.

Phase 12 — ChatSessionSnapshot
Collapses ~20 flat chat AppState fields into a single immutable snapshot.
All raw fields are preserved on AppState for backward-compat; this snapshot
is the canonical view for UI and services.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "ChatMessageSnapshot",
    "ChatWorkspaceEntityRef",
    "ChatContextInfo",
    "ChatSessionSnapshot",
]


@dataclass(frozen=True, slots=True)
class ChatMessageSnapshot:
    """Canonical typed chat message.

    Used as the authoritative message type in ChatSessionSnapshot.
    ``ChatHistoryMessage`` in app_state.py is preserved for backward
    compatibility but new code should use this type.
    """

    role: str = ""
    content: str = ""


@dataclass(frozen=True, slots=True)
class ChatWorkspaceEntityRef:
    """Reference to the workspace entity attached to the current chat."""

    entity_id: str = ""
    entity_type: str = ""
    title: str = ""
    description: str = ""
    url: str = ""
    path: str = ""

    @property
    def is_set(self) -> bool:
        """True when an entity is attached."""
        return bool(self.entity_id)


@dataclass(frozen=True, slots=True)
class ChatContextInfo:
    """Chat context metadata."""

    sources: tuple[str, ...] = ()
    token_estimate: int = 0
    snippet_count: int = 0
    workspace_id: str = ""


@dataclass(frozen=True, slots=True)
class ChatSessionSnapshot:
    """Consolidated typed projection of all Chat Session AppState fields.

    Phase 12 deliverable — collapses ~20 flat fields into one immutable
    snapshot. The raw fields on AppState are kept for backward compatibility;
    this snapshot is the authoritative view for UI rendering.
    """

    # Lifecycle
    active_request_id: str = ""
    last_request_id: str = ""
    status: str = "idle"
    streaming: bool = False
    session_key: str = "default"
    last_error: str = ""

    # Stream state
    stream_buffer: str = ""
    stream_revision: int = 0

    # Pending / started user input
    pending_user_text: str = ""
    started_user_text: str = ""

    # Rendered output
    last_assistant_message: str = ""

    # Context
    context: ChatContextInfo = field(default_factory=ChatContextInfo)

    # Workspace entity attached to chat
    workspace_entity: ChatWorkspaceEntityRef = field(
        default_factory=ChatWorkspaceEntityRef
    )

    # History
    history_messages: tuple[ChatMessageSnapshot, ...] = ()
    history_count: int = 0
    history_revision: int = 0

    # Change-detection counter (increments on every reducer call)
    revision: int = 0