"""Goal Engine contracts for Brain scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_command_center.domain.correlation import CorrelationContext


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class GoalStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SuccessVerifier(str, Enum):
    MANUAL = "manual"
    EVENT = "event"
    WORLD_MODEL_QUERY = "world_model_query"


@dataclass(frozen=True, slots=True)
class SuccessCriteria:
    id: str
    description: str
    verifier: SuccessVerifier = SuccessVerifier.MANUAL
    expected: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "verifier": self.verifier.value,
            "expected": dict(self.expected),
        }


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    goal_id: str
    title: str
    description: str = ""
    depends_on: tuple[str, ...] = ()
    status: TaskStatus = TaskStatus.PENDING
    success_criteria: tuple[SuccessCriteria, ...] = ()
    correlation: CorrelationContext = field(default_factory=CorrelationContext.new)

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "depends_on": list(self.depends_on),
            "status": self.status.value,
            "success_criteria": [item.to_payload() for item in self.success_criteria],
            "correlation": self.correlation.to_payload(),
        }


@dataclass(frozen=True, slots=True)
class Goal:
    id: str
    title: str
    description: str = ""
    priority: Priority = Priority.NORMAL
    depends_on: tuple[str, ...] = ()
    tasks: tuple[Task, ...] = ()
    success_criteria: tuple[SuccessCriteria, ...] = ()
    status: GoalStatus = GoalStatus.DRAFT
    correlation: CorrelationContext = field(default_factory=CorrelationContext.new)

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "depends_on": list(self.depends_on),
            "tasks": [task.to_payload() for task in self.tasks],
            "success_criteria": [item.to_payload() for item in self.success_criteria],
            "status": self.status.value,
            "correlation": self.correlation.to_payload(),
        }
