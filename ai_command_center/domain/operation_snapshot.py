"""OperationSnapshot domain model — reconstructed view of a completed operation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SnapshotSection(str, Enum):
    GOAL = "goal"
    PLAN = "plan"
    EXECUTIONS = "executions"
    AGENTS = "agents"
    MEMORY = "memory"
    JOURNAL = "journal"


@dataclass(frozen=True, slots=True)
class OperationSnapshot:
    """Reconstructed, read-only view of an operation lifecycle.

    Assembled on demand from existing repositories via correlation_id.
    Never persisted directly (except when explicitly archived to operation_archive).
    Sections that could not be reconstructed within timeout are marked unavailable.
    """

    correlation_id: str
    goal_id: str = ""
    goal_title: str = ""
    goal_status: str = ""
    goal_priority: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    agent_ids: tuple[str, ...] = ()
    execution_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    unavailable_sections: tuple[SnapshotSection, ...] = ()
    is_partial: bool = False
    reconstructed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "goal_status": self.goal_status,
            "goal_priority": self.goal_priority,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "agent_ids": list(self.agent_ids),
            "execution_ids": list(self.execution_ids),
            "tags": list(self.tags),
            "unavailable_sections": [s.value for s in self.unavailable_sections],
            "is_partial": self.is_partial,
            "reconstructed_at": self.reconstructed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperationSnapshot:
        return cls(
            correlation_id=str(data.get("correlation_id", "")),
            goal_id=str(data.get("goal_id", "")),
            goal_title=str(data.get("goal_title", "")),
            goal_status=str(data.get("goal_status", "")),
            goal_priority=str(data.get("goal_priority", "")),
            started_at=float(data.get("started_at", 0.0)),
            completed_at=float(data.get("completed_at", 0.0)),
            agent_ids=tuple(str(x) for x in data.get("agent_ids", [])),
            execution_ids=tuple(str(x) for x in data.get("execution_ids", [])),
            tags=tuple(str(x) for x in data.get("tags", [])),
            unavailable_sections=tuple(
                SnapshotSection(s)
                for s in data.get("unavailable_sections", [])
                if s in SnapshotSection._value2member_map_
            ),
            is_partial=bool(data.get("is_partial", False)),
            reconstructed_at=float(data.get("reconstructed_at", time.time())),
        )
