"""
Timeline Event Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the TimelineEvent contract for the Workspace Operating System.
Timeline provides universal event storage for audit, undo, analytics, and debugging.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """
    Universal event storage - audit, undo, analytics, debugging.
    
    Benefits:
    - Activity feed
    - Audit log
    - Undo/redo
    - Event replay
    - Analytics
    - Debugging
    """

    id: UUID
    event_type: str

    entity_id: UUID | None
    entity_type: str | None

    payload: dict[str, Any]

    timestamp: datetime
    user_id: str | None  # Future multi-user support

    # Undo support
    reversible: bool
    undo_data: dict[str, Any] | None

    # Schema versioning
    schema_version: int


# Current schema version
TIMELINE_EVENT_SCHEMA_VERSION = 1
