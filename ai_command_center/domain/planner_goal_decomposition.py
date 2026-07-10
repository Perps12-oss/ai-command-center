"""Goal Decomposition Engine — goal hierarchy and decomposition.

This module defines how goals are decomposed into actionable plans.
Per ACC Planner Constitution Phase C0:
- 06_GOAL_DECOMPOSITION_ENGINE.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GoalType(Enum):
    """Type of goal."""

    TASK = "task"
    PROJECT = "project"
    LIFECYCLE = "lifecycle"
    MAINTENANCE = "maintenance"


class GoalPriority(Enum):
    """Goal priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class GoalOrigin(Enum):
    """Origin of the goal."""

    USER = "user"
    SCHEDULER = "scheduler"
    AUTONOMOUS = "autonomous"


class ObjectiveType(Enum):
    """Type of objective within a goal."""

    PREREQUISITE = "prerequisite"
    PRIMARY = "primary"
    VERIFICATION = "verification"
    CLEANUP = "cleanup"


class TaskType(Enum):
    """Type of task within an objective."""

    AUTOMATED = "automated"
    MANUAL = "manual"
    APPROVAL = "approval"


@dataclass(frozen=True, slots=True)
class GoalContext:
    """Context information for a goal."""

    user_id: str = ""
    workspace_id: str = ""
    project_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "workspaceId": self.workspace_id,
            "projectId": self.project_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoalContext:
        return cls(
            user_id=str(data.get("userId", "")),
            workspace_id=str(data.get("workspaceId", "")),
            project_id=str(data.get("projectId", "")),
        )


@dataclass(frozen=True, slots=True)
class Goal:
    """The user's top-level intent.

    This is the entry point for goal decomposition.
    """

    goal_id: str
    description: str
    goal_type: GoalType = GoalType.TASK
    priority: GoalPriority = GoalPriority.NORMAL
    deadline: str = ""  # ISO8601
    origin: GoalOrigin = GoalOrigin.USER
    constraint_refs: tuple[str, ...] = field(default_factory=tuple)
    context: GoalContext = field(default_factory=GoalContext)
    success_criteria: tuple[str, ...] = field(default_factory=tuple)
    objective_refs: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goalId": self.goal_id,
            "description": self.description,
            "type": self.goal_type.value,
            "priority": self.priority.value,
            "deadline": self.deadline,
            "origin": self.origin.value,
            "constraints": list(self.constraint_refs),
            "context": self.context.to_dict(),
            "successCriteria": list(self.success_criteria),
            "objectives": list(self.objective_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Goal:
        try:
            goal_type = GoalType(data.get("type", GoalType.TASK.value))
        except ValueError:
            goal_type = GoalType.TASK

        try:
            priority = GoalPriority(data.get("priority", GoalPriority.NORMAL.value))
        except ValueError:
            priority = GoalPriority.NORMAL

        try:
            origin = GoalOrigin(data.get("origin", GoalOrigin.USER.value))
        except ValueError:
            origin = GoalOrigin.USER

        return cls(
            goal_id=str(data["goalId"]),
            description=str(data["description"]),
            goal_type=goal_type,
            priority=priority,
            deadline=str(data.get("deadline", "")),
            origin=origin,
            constraint_refs=tuple(str(c) for c in data.get("constraints") or []),
            context=GoalContext.from_dict(data.get("context") or {}),
            success_criteria=tuple(str(s) for s in data.get("successCriteria") or []),
            objective_refs=tuple(str(o) for o in data.get("objectives") or []),
        )


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry policy for tasks."""

    max_retries: int = 3
    backoff: str = "exponential"  # exponential, linear
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000

    def to_dict(self) -> dict[str, Any]:
        return {
            "maxRetries": self.max_retries,
            "backoff": self.backoff,
            "initialDelayMs": self.initial_delay_ms,
            "maxDelayMs": self.max_delay_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetryPolicy:
        return cls(
            max_retries=int(data.get("maxRetries", 3)),
            backoff=str(data.get("backoff", "exponential")),
            initial_delay_ms=int(data.get("initialDelayMs", 1000)),
            max_delay_ms=int(data.get("maxDelayMs", 60000)),
        )


@dataclass(frozen=True, slots=True)
class Objective:
    """A discrete outcome contributing to the goal."""

    objective_id: str
    goal_ref: str
    description: str
    objective_type: ObjectiveType = ObjectiveType.PRIMARY
    priority: GoalPriority = GoalPriority.NORMAL
    depends_on: tuple[str, ...] = field(default_factory=tuple)  # Other objective IDs
    task_refs: tuple[str, ...] = field(default_factory=tuple)
    success_criteria: tuple[str, ...] = field(default_factory=tuple)
    estimated_duration: str = ""  # e.g., "10m", "1h"
    can_fail_independently: bool = True
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "objectiveId": self.objective_id,
            "goalRef": self.goal_ref,
            "description": self.description,
            "type": self.objective_type.value,
            "priority": self.priority.value,
            "dependsOn": list(self.depends_on),
            "tasks": list(self.task_refs),
            "successCriteria": list(self.success_criteria),
            "estimatedDuration": self.estimated_duration,
            "canFailIndependently": self.can_fail_independently,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Objective:
        try:
            objective_type = ObjectiveType(data.get("type", ObjectiveType.PRIMARY.value))
        except ValueError:
            objective_type = ObjectiveType.PRIMARY

        try:
            priority = GoalPriority(data.get("priority", GoalPriority.NORMAL.value))
        except ValueError:
            priority = GoalPriority.NORMAL

        return cls(
            objective_id=str(data["objectiveId"]),
            goal_ref=str(data["goalRef"]),
            description=str(data["description"]),
            objective_type=objective_type,
            priority=priority,
            depends_on=tuple(str(d) for d in data.get("dependsOn") or []),
            task_refs=tuple(str(t) for t in data.get("tasks") or []),
            success_criteria=tuple(str(s) for s in data.get("successCriteria") or []),
            estimated_duration=str(data.get("estimatedDuration", "")),
            can_fail_independently=bool(data.get("canFailIndependently", True)),
            status=str(data.get("status", "pending")),
        )


@dataclass(frozen=True, slots=True)
class Task:
    """A unit of work contributing to an objective."""

    task_id: str
    objective_ref: str
    description: str
    task_type: TaskType = TaskType.AUTOMATED
    required_capabilities: tuple[str, ...] = field(default_factory=tuple)
    depends_on: tuple[str, ...] = field(default_factory=tuple)  # Other task IDs
    action_refs: tuple[str, ...] = field(default_factory=tuple)
    estimated_duration: str = ""  # e.g., "5m"
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    can_be_parallelized: bool = False
    rollback_on_failure: bool = True
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "objectiveRef": self.objective_ref,
            "description": self.description,
            "type": self.task_type.value,
            "requiredCapabilities": list(self.required_capabilities),
            "dependsOn": list(self.depends_on),
            "actions": list(self.action_refs),
            "estimatedDuration": self.estimated_duration,
            "retryPolicy": self.retry_policy.to_dict(),
            "canBeParallelized": self.can_be_parallelized,
            "rollbackOnFailure": self.rollback_on_failure,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        try:
            task_type = TaskType(data.get("type", TaskType.AUTOMATED.value))
        except ValueError:
            task_type = TaskType.AUTOMATED

        return cls(
            task_id=str(data["taskId"]),
            objective_ref=str(data["objectiveRef"]),
            description=str(data["description"]),
            task_type=task_type,
            required_capabilities=tuple(
                str(c) for c in data.get("requiredCapabilities") or []
            ),
            depends_on=tuple(str(d) for d in data.get("dependsOn") or []),
            action_refs=tuple(str(a) for a in data.get("actions") or []),
            estimated_duration=str(data.get("estimatedDuration", "")),
            retry_policy=RetryPolicy.from_dict(data.get("retryPolicy") or {}),
            can_be_parallelized=bool(data.get("canBeParallelized", False)),
            rollback_on_failure=bool(data.get("rollbackOnFailure", True)),
            status=str(data.get("status", "pending")),
        )


@dataclass(frozen=True, slots=True)
class GoalDecomposition:
    """Complete goal decomposition result.

    Contains the full hierarchy from Goal to Objective to Task to Action.
    """

    goal: Goal
    objectives: tuple[Objective, ...] = field(default_factory=tuple)
    tasks: tuple[Task, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal.to_dict(),
            "objectives": [o.to_dict() for o in self.objectives],
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoalDecomposition:
        return cls(
            goal=Goal.from_dict(data["goal"]),
            objectives=tuple(Objective.from_dict(o) for o in data.get("objectives") or []),
            tasks=tuple(Task.from_dict(t) for t in data.get("tasks") or []),
        )

    @property
    def total_objectives(self) -> int:
        """Total number of objectives."""
        return len(self.objectives)

    @property
    def total_tasks(self) -> int:
        """Total number of tasks."""
        return len(self.tasks)

    def get_objective_by_id(self, objective_id: str) -> Objective | None:
        """Find an objective by ID."""
        for obj in self.objectives:
            if obj.objective_id == objective_id:
                return obj
        return None

    def get_task_by_id(self, task_id: str) -> Task | None:
        """Find a task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_tasks_for_objective(self, objective_id: str) -> tuple[Task, ...]:
        """Get all tasks for a specific objective."""
        return tuple(t for t in self.tasks if t.objective_ref == objective_id)


@dataclass(frozen=True, slots=True)
class AbandonmentReason:
    """Reason for goal abandonment."""

    reason_type: str = ""  # user_requested, max_retries_exceeded, etc.
    description: str = ""
    timestamp: str = ""  # ISO8601
    impact: str = ""  # Impact assessment
    partial_completion: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.reason_type,
            "description": self.description,
            "timestamp": self.timestamp,
            "impact": self.impact,
            "partialCompletion": self.partial_completion,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AbandonmentReason:
        return cls(
            reason_type=str(data.get("type", "")),
            description=str(data.get("description", "")),
            timestamp=str(data.get("timestamp", "")),
            impact=str(data.get("impact", "")),
            partial_completion=bool(data.get("partialCompletion", False)),
        )


# Granularity standards from spec
GRANULARITY_STANDARDS = {
    "too_coarse": {
        "symptoms": ["multi-month timeline", "100+ actions", "multiple teams"],
        "action": "split_into_multiple_goals",
    },
    "appropriate": {
        "criteria": ["single sprint scope", "<50 actions", "single team"],
    },
    "too_fine": {
        "symptoms": ["single action goals", "no meaningful decomposition"],
        "action": "merge_into_coarser_goal",
    },
}

# Maximum decomposition depth
MAX_DECOMPOSITION_DEPTH = 4
