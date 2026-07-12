"""Goal domain model.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ai_command_center.orchestration.goals.goal_status import GoalStatus


@dataclass
class Goal:
    """A persistent goal that survives restarts.

    Goals represent user intentions that persist across sessions and
    can be broken down into tasks for execution.

    Attributes:
        id: Unique identifier
        title: Short descriptive title
        description: Detailed description of the goal
        status: Current lifecycle state
        created_at: When the goal was created
        updated_at: When the goal was last modified
        created_by: Identifier of who/what created this goal
        parent_goal_id: Optional parent goal for hierarchical goals
        tags: Labels for categorization and filtering
        metadata: Additional arbitrary data
        priority: Relative priority (higher = more important)
        deadline: Optional target completion time
    """

    id: str
    title: str
    description: str
    status: GoalStatus = GoalStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "user"
    parent_goal_id: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    deadline: datetime | None = None

    def can_transition_to(self, target_status: GoalStatus) -> bool:
        """Check if transition to target status is valid."""
        return self.status.can_transition_to(target_status)

    def transition_to(self, target_status: GoalStatus) -> Goal:
        """Return a new Goal with the updated status.

        This is an immutable operation - returns a new instance.
        """
        if not self.can_transition_to(target_status):
            raise ValueError(
                f"Cannot transition from {self.status.value} to {target_status.value}"
            )

        return Goal(
            id=self.id,
            title=self.title,
            description=self.description,
            status=target_status,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            created_by=self.created_by,
            parent_goal_id=self.parent_goal_id,
            tags=self.tags,
            metadata=self.metadata,
            priority=self.priority,
            deadline=self.deadline,
        )

    def activate(self) -> Goal:
        """Activate the goal. Shorthand for transition_to(ACTIVE)."""
        return self.transition_to(GoalStatus.ACTIVE)

    def pause(self) -> Goal:
        """Pause the goal. Shorthand for transition_to(PAUSED)."""
        return self.transition_to(GoalStatus.PAUSED)

    def complete(self) -> Goal:
        """Complete the goal. Shorthand for transition_to(COMPLETED)."""
        return self.transition_to(GoalStatus.COMPLETED)

    def abandon(self) -> Goal:
        """Abandon the goal. Shorthand for transition_to(ABANDONED)."""
        return self.transition_to(GoalStatus.ABANDONED)

    def block(self) -> Goal:
        """Block the goal. Shorthand for transition_to(BLOCKED)."""
        return self.transition_to(GoalStatus.BLOCKED)

    def fail(self) -> Goal:
        """Mark goal as failed. Shorthand for transition_to(FAILED)."""
        return self.transition_to(GoalStatus.FAILED)

    def is_terminal(self) -> bool:
        """Return True if goal is in a terminal state."""
        return self.status.is_terminal

    def is_active(self) -> bool:
        """Return True if goal is being actively worked on."""
        return self.status.is_active

    @property
    def is_root_goal(self) -> bool:
        """Return True if this is a top-level goal (no parent)."""
        return self.parent_goal_id is None

    def with_priority(self, priority: int) -> Goal:
        """Return a new Goal with updated priority."""
        return Goal(
            id=self.id,
            title=self.title,
            description=self.description,
            status=self.status,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            created_by=self.created_by,
            parent_goal_id=self.parent_goal_id,
            tags=self.tags,
            metadata=self.metadata,
            priority=priority,
            deadline=self.deadline,
        )

    def with_tags(self, tags: list[str]) -> Goal:
        """Return a new Goal with updated tags."""
        return Goal(
            id=self.id,
            title=self.title,
            description=self.description,
            status=self.status,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            created_by=self.created_by,
            parent_goal_id=self.parent_goal_id,
            tags=tags,
            metadata=self.metadata,
            priority=self.priority,
            deadline=self.deadline,
        )


__all__ = ["Goal"]
