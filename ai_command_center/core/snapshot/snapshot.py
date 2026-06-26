"""
State Snapshot Contract - FROZEN ARCHITECTURE SPECIFICATION

This module defines the StateSnapshot contract for the Workspace Operating System.
State snapshots provide checkpoint, restore, undo architecture.

FROZEN: Phase 0 - Universal Foundation
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    """
    System state snapshot - checkpoint, restore, undo.
    
    Use Cases:
    - Undo (reverse to previous snapshot)
    - Restore (recover from error state)
    - Replay (debugging by replaying events from snapshot)
    - Migration (test schema migrations on snapshots)
    """

    id: UUID
    snapshot_type: str  # checkpoint, manual, auto

    # Entity state
    entities: dict[UUID, dict[str, Any]]
    relationships: dict[UUID, dict[str, Any]]

    # Workspace state
    active_workspace_id: UUID | None
    workspace_layouts: dict[UUID, dict[str, Any]]

    # Settings state
    settings: dict[str, Any]

    # Metadata
    created_at: datetime
    description: str
    schema_version: int


# Snapshot types
SNAPSHOT_TYPE_CHECKPOINT = "checkpoint"
SNAPSHOT_TYPE_MANUAL = "manual"
SNAPSHOT_TYPE_AUTO = "auto"

# Valid snapshot types for validation
VALID_SNAPSHOT_TYPES = {
    SNAPSHOT_TYPE_CHECKPOINT,
    SNAPSHOT_TYPE_MANUAL,
    SNAPSHOT_TYPE_AUTO,
}

# Current schema version
SNAPSHOT_SCHEMA_VERSION = 1


def validate_snapshot_type(snapshot_type: str) -> bool:
    """Validate that snapshot_type is a recognized snapshot type."""
    return snapshot_type in VALID_SNAPSHOT_TYPES
