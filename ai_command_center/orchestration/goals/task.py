"""Task model — executable units within a task graph.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """Lifecycle states for a Task."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def is_terminal(self) -> bool:
        """Return True if this is a terminal state."""
        return self in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED}

    @property
    def is_active(self) -> bool:
        """Return True if task is being executed."""
        return self == TaskStatus.RUNNING


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class Task:
    """An executable unit within a TaskGraph.

    Tasks are the atomic units of work that can be executed by agents.
    They form a DAG (Directed Acyclic Graph) with dependencies.

    Attributes:
        id: Unique identifier
        goal_id: Parent goal this task belongs to
        title: Short description of the task
        description: Detailed instructions
        status: Current lifecycle state
        priority: Relative priority within the goal
        created_at: When the task was created
        updated_at: When the task was last modified
        depends_on: List of task IDs that must complete first
        assigned_to: Agent ID assigned to execute this task
        result: Result data from execution
        error: Error message if failed
        estimated_duration: Estimated time in seconds
        actual_duration: Actual time taken in seconds
        retry_count: Number of execution attempts
        max_retries: Maximum retry attempts allowed
        metadata: Additional arbitrary data
    """

    id: str
    goal_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    depends_on: list[str] = field(default_factory=list)
    assigned_to: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    estimated_duration: int | None = None  # seconds
    actual_duration: int | None = None  # seconds
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def can_execute(self) -> bool:
        """Return True if task is ready to be executed."""
        return self.status in {TaskStatus.READY, TaskStatus.PENDING}

    @property
    def is_blocked(self) -> bool:
        """Return True if task is blocked by dependencies."""
        return self.status == TaskStatus.BLOCKED

    @property
    def has_failed_permanently(self) -> bool:
        """Return True if task has exceeded max retries."""
        return self.status == TaskStatus.FAILED and self.retry_count >= self.max_retries

    def can_retry(self) -> bool:
        """Return True if task can be retried."""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def assign(self, agent_id: str) -> Task:
        """Return a new Task assigned to an agent."""
        return Task(
            id=self.id,
            goal_id=self.goal_id,
            title=self.title,
            description=self.description,
            status=self.status,
            priority=self.priority,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            depends_on=self.depends_on,
            assigned_to=agent_id,
            result=self.result,
            error=self.error,
            estimated_duration=self.estimated_duration,
            actual_duration=self.actual_duration,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            metadata=self.metadata,
        )

    def complete(self, result: dict[str, Any] | None = None, duration: int | None = None) -> Task:
        """Return a new completed Task."""
        return Task(
            id=self.id,
            goal_id=self.goal_id,
            title=self.title,
            description=self.description,
            status=TaskStatus.COMPLETED,
            priority=self.priority,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            depends_on=self.depends_on,
            assigned_to=self.assigned_to,
            result=result or {},
            error=self.error,
            estimated_duration=self.estimated_duration,
            actual_duration=duration,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            metadata=self.metadata,
        )

    def fail(self, error: str, retry: bool = False) -> Task:
        """Return a new failed Task."""
        new_retry_count = self.retry_count + 1 if retry else self.retry_count
        new_status = TaskStatus.PENDING if (retry and new_retry_count < self.max_retries) else TaskStatus.FAILED

        return Task(
            id=self.id,
            goal_id=self.goal_id,
            title=self.title,
            description=self.description,
            status=new_status,
            priority=self.priority,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            depends_on=self.depends_on,
            assigned_to=self.assigned_to,
            result=self.result,
            error=error,
            estimated_duration=self.estimated_duration,
            actual_duration=self.actual_duration,
            retry_count=new_retry_count,
            max_retries=self.max_retries,
            metadata=self.metadata,
        )

    def start(self) -> Task:
        """Return a new Task in RUNNING state."""
        return Task(
            id=self.id,
            goal_id=self.goal_id,
            title=self.title,
            description=self.description,
            status=TaskStatus.RUNNING,
            priority=self.priority,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            depends_on=self.depends_on,
            assigned_to=self.assigned_to,
            result=self.result,
            error=self.error,
            estimated_duration=self.estimated_duration,
            actual_duration=self.actual_duration,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            metadata=self.metadata,
        )


__all__ = ["Task", "TaskStatus", "TaskPriority"]
