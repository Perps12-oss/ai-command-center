"""
Event Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the Event contract for the Workspace Operating System.
EventBus is the nervous system - everything publishes events, nothing talks directly.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Event:
    """
    Universal event envelope.
    
    EventBus is the nervous system of the Workspace OS.
    All major operations publish events for:
    - Timeline/audit logging
    - AppState updates
    - Plugin extensibility
    - Observability
    - Undo/replay
    """

    id: UUID
    event_type: str
    timestamp: datetime

    entity_id: UUID | None
    entity_type: str | None

    payload: dict[str, Any]

    source: str


# Entity events
EVENT_ENTITY_CREATED = "entity.created"
EVENT_ENTITY_UPDATED = "entity.updated"
EVENT_ENTITY_DELETED = "entity.deleted"
EVENT_ENTITY_RELATIONSHIPS_CHANGED = "entity.relationships.changed"

# Relationship events
EVENT_RELATIONSHIP_CREATED = "relationship.created"
EVENT_RELATIONSHIP_DELETED = "relationship.deleted"
EVENT_RELATIONSHIP_QUERY_REQUEST = "relationship.query.request"

# Action events
EVENT_ACTION_REGISTERED = "action.registered"
EVENT_ACTION_INVOKED = "action.invoked"
EVENT_ACTION_COMPLETED = "action.completed"
EVENT_ACTION_FAILED = "action.failed"

# Workspace events
EVENT_WORKSPACE_CREATED = "workspace.created"
EVENT_WORKSPACE_ACTIVATED = "workspace.activated"
EVENT_WORKSPACE_DEACTIVATED = "workspace.deactivated"
EVENT_WORKSPACE_LAYOUT_CHANGED = "workspace.layout.changed"

# Timeline events (all major actions)
EVENT_TIMELINE_EVENT = "timeline.event"

# Search events
EVENT_SEARCH_EXECUTED = "search.executed"
EVENT_SEARCH_RESULTS = "search.results"

# AI events
EVENT_AGENT_SPAWNED = "agent.spawned"
EVENT_AGENT_TERMINATED = "agent.terminated"
EVENT_AI_ACTION_INVOKED = "ai.action.invoked"
EVENT_AI_ACTION_COMPLETED = "ai.action.completed"

# Plugin events
EVENT_PLUGIN_LOADED = "plugin.loaded"
EVENT_PLUGIN_UNLOADED = "plugin.unloaded"
EVENT_PLUGIN_REGISTERED_ENTITY = "plugin.registered.entity"
EVENT_PLUGIN_REGISTERED_ACTION = "plugin.registered.action"
EVENT_PLUGIN_REGISTERED_VIEW = "plugin.registered.view"
EVENT_PLUGIN_REGISTERED_SEARCH_PROVIDER = "plugin.registered.search_provider"

# Observability events
EVENT_OBSERVABILITY_METRIC = "observability.metric"
EVENT_OBSERVABILITY_ERROR = "observability.error"

# Permission events
EVENT_PERMISSION_CHECK = "permission.check"
EVENT_PERMISSION_DENIED = "permission.denied"

# State snapshot events
EVENT_SNAPSHOT_CREATED = "snapshot.created"
EVENT_SNAPSHOT_RESTORED = "snapshot.restored"

# Valid event types for validation
VALID_EVENT_TYPES = {
    EVENT_ENTITY_CREATED,
    EVENT_ENTITY_UPDATED,
    EVENT_ENTITY_DELETED,
    EVENT_ENTITY_RELATIONSHIPS_CHANGED,
    EVENT_RELATIONSHIP_CREATED,
    EVENT_RELATIONSHIP_DELETED,
    EVENT_RELATIONSHIP_QUERY_REQUEST,
    EVENT_ACTION_REGISTERED,
    EVENT_ACTION_INVOKED,
    EVENT_ACTION_COMPLETED,
    EVENT_ACTION_FAILED,
    EVENT_WORKSPACE_CREATED,
    EVENT_WORKSPACE_ACTIVATED,
    EVENT_WORKSPACE_DEACTIVATED,
    EVENT_WORKSPACE_LAYOUT_CHANGED,
    EVENT_TIMELINE_EVENT,
    EVENT_SEARCH_EXECUTED,
    EVENT_SEARCH_RESULTS,
    EVENT_AGENT_SPAWNED,
    EVENT_AGENT_TERMINATED,
    EVENT_AI_ACTION_INVOKED,
    EVENT_AI_ACTION_COMPLETED,
    EVENT_PLUGIN_LOADED,
    EVENT_PLUGIN_UNLOADED,
    EVENT_PLUGIN_REGISTERED_ENTITY,
    EVENT_PLUGIN_REGISTERED_ACTION,
    EVENT_PLUGIN_REGISTERED_VIEW,
    EVENT_PLUGIN_REGISTERED_SEARCH_PROVIDER,
    EVENT_OBSERVABILITY_METRIC,
    EVENT_OBSERVABILITY_ERROR,
    EVENT_PERMISSION_CHECK,
    EVENT_PERMISSION_DENIED,
    EVENT_SNAPSHOT_CREATED,
    EVENT_SNAPSHOT_RESTORED,
}


def validate_event_type(event_type: str) -> bool:
    """Validate that event_type is a recognized event type."""
    return event_type in VALID_EVENT_TYPES
