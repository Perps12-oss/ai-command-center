"""UndoReplayFramework — timeline-based recovery for workspace state.

Reference: docs/plans/PHASE_10_WORLD_MODEL_PLAN.md Section 10.5
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions that can be undone/redone."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"  # Command execution
    APPROVE = "approve"
    REJECT = "reject"


class TimelineStatus(str, Enum):
    """Status of the timeline system."""

    IDLE = "idle"
    RECORDING = "recording"
    UNDOING = "undoing"
    REPLAYING = "replaying"


@dataclass
class TimelineEntry:
    """A single entry in the timeline."""

    id: str
    action_type: ActionType
    entity_type: str  # e.g., "goal", "task", "file"
    entity_id: str
    before_state: dict[str, Any] | None = None  # State before action
    after_state: dict[str, Any] | None = None  # State after action
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = "system"
    correlation_id: str | None = None
    description: str = ""
    can_undo: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "description": self.description,
            "can_undo": self.can_undo,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEntry:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            action_type=ActionType(data["action_type"]),
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            before_state=data.get("before_state"),
            after_state=data.get("after_state"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data.get("user_id", "system"),
            correlation_id=data.get("correlation_id"),
            description=data.get("description", ""),
            can_undo=data.get("can_undo", True),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Snapshot:
    """A point-in-time snapshot of system state."""

    id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    goals: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "goals": self.goals,
            "tasks": self.tasks,
            "entities": self.entities,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Snapshot:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            goals=data.get("goals", []),
            tasks=data.get("tasks", []),
            entities=data.get("entities", []),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> Snapshot:
        """Deserialize from JSON."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class UndoResult:
    """Result of an undo operation."""

    success: bool
    undone_entry: TimelineEntry | None = None
    message: str = ""
    restored_state: dict[str, Any] | None = None


class Timeline:
    """Manages timeline of actions with undo/redo capability.

    The Timeline provides:
    - Recording of all significant actions
    - Undo functionality with state restoration
    - Replay capability for recovery
    - Snapshot creation for rollback points
    """

    MAX_ENTRIES = 1000  # Maximum entries to keep in memory
    SNAPSHOT_INTERVAL = 50  # Create snapshot every N entries

    def __init__(
        self,
        state_provider: StateProvider | None = None,
        max_entries: int | None = None,
    ) -> None:
        self._entries: list[TimelineEntry] = []
        self._current_position = -1  # -1 means at the end
        self._snapshots: list[Snapshot] = []
        self._state_provider = state_provider
        self._status = TimelineStatus.IDLE
        self._max_entries = max_entries or self.MAX_ENTRIES

    @property
    def status(self) -> TimelineStatus:
        """Get current timeline status."""
        return self._status

    @property
    def entries(self) -> list[TimelineEntry]:
        """Get all timeline entries."""
        return self._entries.copy()

    @property
    def can_undo(self) -> bool:
        """Return True if there are entries to undo."""
        return self._current_position >= 0

    @property
    def can_redo(self) -> bool:
        """Return True if there are entries to redo."""
        return self._current_position < len(self._entries) - 1

    def record(
        self,
        action_type: ActionType,
        entity_type: str,
        entity_id: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        user_id: str = "system",
        description: str = "",
        can_undo: bool = True,
    ) -> TimelineEntry:
        """Record an action in the timeline.

        Args:
            action_type: Type of action
            entity_type: Type of entity affected
            entity_id: ID of the entity
            before_state: State before the action
            after_state: State after the action
            user_id: Who performed the action
            description: Human-readable description
            can_undo: Whether this action can be undone

        Returns:
            The created TimelineEntry
        """
        import uuid

        # Clear any redo history
        if self._current_position < len(self._entries) - 1:
            self._entries = self._entries[: self._current_position + 1]

        entry = TimelineEntry(
            id=str(uuid.uuid4()),
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            user_id=user_id,
            description=description,
            can_undo=can_undo,
        )

        self._entries.append(entry)
        self._current_position = len(self._entries) - 1

        # Trim if exceeds max
        self._trim()

        # Create snapshot if needed
        if len(self._entries) % self.SNAPSHOT_INTERVAL == 0:
            self.create_snapshot()

        logger.info(
            "Recorded: %s %s %s",
            action_type.value,
            entity_type,
            entity_id,
        )

        return entry

    def undo(self) -> UndoResult:
        """Undo the most recent action.

        Returns:
            UndoResult indicating success/failure
        """
        if not self.can_undo:
            return UndoResult(
                success=False,
                message="Nothing to undo",
            )

        self._status = TimelineStatus.UNDOING

        try:
            entry = self._entries[self._current_position]

            if not entry.can_undo:
                return UndoResult(
                    success=False,
                    message=f"Action cannot be undone: {entry.description}",
                    undone_entry=entry,
                )

            # Restore state if we have before_state and a state provider
            restored = None
            if entry.before_state and self._state_provider:
                try:
                    self._state_provider.restore_state(
                        entry.entity_type,
                        entry.entity_id,
                        entry.before_state,
                    )
                    restored = entry.before_state
                except Exception as e:
                    logger.error("Failed to restore state: %s", e)
                    return UndoResult(
                        success=False,
                        undone_entry=entry,
                        message=f"Failed to restore state: {e}",
                    )

            self._current_position -= 1

            logger.info("Undid: %s", entry.description)

            return UndoResult(
                success=True,
                undone_entry=entry,
                message=f"Undone: {entry.description}",
                restored_state=restored,
            )

        finally:
            self._status = TimelineStatus.IDLE

    def redo(self) -> UndoResult:
        """Redo the most recently undone action.

        Returns:
            UndoResult indicating success/failure
        """
        if not self.can_redo:
            return UndoResult(
                success=False,
                message="Nothing to redo",
            )

        self._current_position += 1
        entry = self._entries[self._current_position]

        # Apply state if we have after_state and a state provider
        if entry.after_state and self._state_provider:
            try:
                self._state_provider.restore_state(
                    entry.entity_type,
                    entry.entity_id,
                    entry.after_state,
                )
            except Exception as e:
                logger.error("Failed to replay state: %s", e)
                return UndoResult(
                    success=False,
                    undone_entry=entry,
                    message=f"Failed to replay state: {e}",
                )

        logger.info("Redid: %s", entry.description)

        return UndoResult(
            success=True,
            undone_entry=entry,
            message=f"Redid: {entry.description}",
            restored_state=entry.after_state,
        )

    def create_snapshot(self, metadata: dict[str, Any] | None = None) -> Snapshot:
        """Create a snapshot of current state.

        Args:
            metadata: Optional metadata to attach

        Returns:
            The created Snapshot
        """
        import uuid

        self._status = TimelineStatus.RECORDING

        try:
            snapshot = Snapshot(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                metadata=metadata or {},
            )

            # Gather state from provider if available
            if self._state_provider:
                snapshot.goals = self._state_provider.get_goals()
                snapshot.tasks = self._state_provider.get_tasks()
                snapshot.entities = self._state_provider.get_entities()

            self._snapshots.append(snapshot)
            logger.info("Created snapshot: %s", snapshot.id)

            return snapshot

        finally:
            self._status = TimelineStatus.IDLE

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore state from a snapshot.

        Args:
            snapshot_id: ID of the snapshot to restore

        Returns:
            True if successful
        """
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            logger.error("Snapshot not found: %s", snapshot_id)
            return False

        if not self._state_provider:
            logger.error("No state provider configured")
            return False

        try:
            self._state_provider.restore_snapshot(snapshot)
            logger.info("Restored snapshot: %s", snapshot_id)
            return True
        except Exception as e:
            logger.error("Failed to restore snapshot: %s", e)
            return False

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """Get a snapshot by ID."""
        for snapshot in self._snapshots:
            if snapshot.id == snapshot_id:
                return snapshot
        return None

    def get_snapshots(self) -> list[Snapshot]:
        """Get all snapshots."""
        return self._snapshots.copy()

    def get_entries_since(self, timestamp: datetime) -> list[TimelineEntry]:
        """Get all entries since a timestamp."""
        return [e for e in self._entries if e.timestamp >= timestamp]

    def get_entries_for_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[TimelineEntry]:
        """Get all entries for a specific entity."""
        return [
            e for e in self._entries
            if e.entity_type == entity_type and e.entity_id == entity_id
        ]

    def _trim(self) -> None:
        """Trim entries if exceeds max."""
        if len(self._entries) > self._max_entries:
            # Keep the most recent entries
            excess = len(self._entries) - self._max_entries
            self._entries = self._entries[excess:]


class StateProvider:
    """Abstract interface for providing/restoring state."""

    def get_goals(self) -> list[dict[str, Any]]:
        """Get current goals state."""
        raise NotImplementedError

    def get_tasks(self) -> list[dict[str, Any]]:
        """Get current tasks state."""
        raise NotImplementedError

    def get_entities(self) -> list[dict[str, Any]]:
        """Get current entities state."""
        raise NotImplementedError

    def restore_state(
        self,
        entity_type: str,
        entity_id: str,
        state: dict[str, Any],
    ) -> None:
        """Restore state for a specific entity."""
        raise NotImplementedError

    def restore_snapshot(self, snapshot: Snapshot) -> None:
        """Restore a full snapshot."""
        raise NotImplementedError


__all__ = [
    "ActionType",
    "Snapshot",
    "StateProvider",
    "Timeline",
    "TimelineEntry",
    "TimelineStatus",
    "UndoResult",
]
