"""JournalEntry domain model — in-memory projection of operation activity."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JournalEntryKind(str, Enum):
    GOAL_STATE = "goal_state"
    PLAN_GENERATED = "plan_generated"
    EXECUTION_STEP = "execution_step"
    TOOL_CALL = "tool_call"
    AGENT_ACTION = "agent_action"
    PERMISSION_REQUEST = "permission_request"
    MEMORY_STORED = "memory_stored"
    OBSERVATION = "observation"


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """Immutable journal entry — one event in the operation lifecycle feed.

    Assembled from EventBus payloads; never persisted directly.
    The underlying source repositories remain queryable for replay.
    """

    entry_id: int
    correlation_id: str
    kind: JournalEntryKind
    summary: str
    object_id: str = ""
    object_type: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_payload(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "correlation_id": self.correlation_id,
            "kind": self.kind.value,
            "summary": self.summary,
            "object_id": self.object_id,
            "object_type": self.object_type,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any], entry_id: int) -> JournalEntry:
        return cls(
            entry_id=entry_id,
            correlation_id=str(payload.get("correlation_id", "")),
            kind=JournalEntryKind(str(payload.get("kind", JournalEntryKind.GOAL_STATE.value))),
            summary=str(payload.get("summary", "")),
            object_id=str(payload.get("object_id", "")),
            object_type=str(payload.get("object_type", "")),
            timestamp=float(payload.get("timestamp", time.time())),
        )
