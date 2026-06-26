"""
Error Event Contract - FROZEN ARCHITECTURE SPECIFICATION

Defines the error event model for Timeline. Raw diagnostics remain in Observability.

FROZEN: Phase 2 - Workspace OS Integration
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    """
    Error event stored in Timeline.
    
    Concerns:
    - Timeline stores the event (what happened, when, to what entity)
    - Observability stores diagnostics (stack traces, context, metrics)
    
    This separation keeps Timeline as a user-readable activity log and
    Observability as the diagnostic layer.
    """

    id: UUID
    event_type: str  # ActionFailed, EntityCreationFailed, SearchFailed, etc.

    entity_id: UUID | None
    entity_type: str | None

    error_message: str
    error_code: str | None

    timestamp: datetime

    # Source metadata
    source: str = "system"
    user_id: str | None = None


# Common error event types
ERROR_EVENT_ACTION_FAILED = "action.failed"
ERROR_EVENT_ENTITY_CREATION_FAILED = "entity.creation.failed"
ERROR_EVENT_ENTITY_UPDATE_FAILED = "entity.update.failed"
ERROR_EVENT_ENTITY_DELETION_FAILED = "entity.deletion.failed"
ERROR_EVENT_SEARCH_FAILED = "search.failed"
ERROR_EVENT_RELATIONSHIP_FAILED = "relationship.failed"
ERROR_EVENT_WORKFLOW_FAILED = "workflow.failed"
ERROR_EVENT_TOOL_FAILED = "tool.failed"
ERROR_EVENT_MIGRATION_FAILED = "migration.failed"
ERROR_EVENT_AI_ACTION_FAILED = "ai.action.failed"

VALID_ERROR_EVENT_TYPES = {
    ERROR_EVENT_ACTION_FAILED,
    ERROR_EVENT_ENTITY_CREATION_FAILED,
    ERROR_EVENT_ENTITY_UPDATE_FAILED,
    ERROR_EVENT_ENTITY_DELETION_FAILED,
    ERROR_EVENT_SEARCH_FAILED,
    ERROR_EVENT_RELATIONSHIP_FAILED,
    ERROR_EVENT_WORKFLOW_FAILED,
    ERROR_EVENT_TOOL_FAILED,
    ERROR_EVENT_MIGRATION_FAILED,
    ERROR_EVENT_AI_ACTION_FAILED,
}

ERROR_EVENT_SCHEMA_VERSION = 1


def create_error_event(
    event_type: str,
    error_message: str,
    entity_id: UUID | None = None,
    entity_type: str | None = None,
    error_code: str | None = None,
    source: str = "system",
    user_id: str | None = None,
) -> ErrorEvent:
    """Factory for creating error events."""
    return ErrorEvent(
        id=uuid4(),
        event_type=event_type,
        entity_id=entity_id,
        entity_type=entity_type,
        error_message=error_message,
        error_code=error_code,
        timestamp=datetime.utcnow(),
        source=source,
        user_id=user_id,
    )


def validate_error_event_type(event_type: str) -> bool:
    """Validate that event_type is a recognized error event type."""
    return event_type in VALID_ERROR_EVENT_TYPES
