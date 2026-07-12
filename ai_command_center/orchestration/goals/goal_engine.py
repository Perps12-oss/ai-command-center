"""GoalEngine — manages goal lifecycle and execution.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.1
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ai_command_center.orchestration.goals.goal import Goal
from ai_command_center.orchestration.goals.goal_status import GoalStatus
from ai_command_center.orchestration.goals.task_graph import TaskGraph

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class GoalEngine:
    """Manages goal lifecycle and coordinates execution.

    The GoalEngine is responsible for:
    - Creating and activating goals
    - Tracking goal state transitions
    - Coordinating with the TaskGraph for execution
    - Publishing lifecycle events to EventBus

    This is a service class that should be instantiated at the
    composition root and injected where needed.
    """

    def __init__(
        self,
        bus: EventBus,
        repository: GoalEngineRepository | None = None,
    ) -> None:
        self._bus = bus
        self._repository = repository or InMemoryGoalRepository()
        self._active_goals: dict[str, Goal] = {}

    # ============ Goal CRUD ============

    def create_goal(
        self,
        title: str,
        description: str,
        goal_id: str | None = None,
        created_by: str = "user",
        tags: list[str] | None = None,
        priority: int = 0,
        parent_goal_id: str | None = None,
    ) -> Goal:
        """Create a new goal in DRAFT status.

        Args:
            title: Short descriptive title
            description: Detailed description
            goal_id: Optional ID (generated if not provided)
            created_by: Who/what created this goal
            tags: Optional labels
            priority: Relative priority
            parent_goal_id: Optional parent for hierarchical goals

        Returns:
            The newly created Goal
        """
        import uuid

        goal = Goal(
            id=goal_id or str(uuid.uuid4()),
            title=title,
            description=description,
            status=GoalStatus.DRAFT,
            created_by=created_by,
            tags=tags or [],
            priority=priority,
            parent_goal_id=parent_goal_id,
        )

        self._repository.save(goal)
        self._bus.publish(
            "goal.created",
            {
                "goal_id": goal.id,
                "title": goal.title,
                "created_by": goal.created_by,
            },
            source="goal_engine",
        )

        logger.info("Created goal: %s (%s)", goal.id, goal.title)
        return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        """Get a goal by ID."""
        return self._repository.get(goal_id)

    def get_goals_by_status(self, status: GoalStatus) -> list[Goal]:
        """Get all goals with a specific status."""
        return self._repository.get_by_status(status)

    def get_active_goals(self) -> list[Goal]:
        """Get all active (non-terminal) goals."""
        return self._repository.get_active()

    # ============ Goal Lifecycle ============

    def activate(self, goal_id: str) -> Goal | None:
        """Activate a goal (transition from DRAFT to ACTIVE).

        Returns:
            The updated goal, or None if not found
        """
        goal = self._repository.get(goal_id)
        if not goal:
            return None

        try:
            updated_goal = goal.activate()
            self._update_goal(updated_goal)
            self._active_goals[goal_id] = updated_goal

            self._bus.publish(
                "goal.activated",
                {
                    "goal_id": goal_id,
                    "title": updated_goal.title,
                },
                source="goal_engine",
            )

            return updated_goal

        except ValueError as e:
            logger.error("Cannot activate goal %s: %s", goal_id, e)
            raise

    def pause(self, goal_id: str) -> Goal | None:
        """Pause an active goal."""
        goal = self._repository.get(goal_id)
        if not goal:
            return None

        try:
            updated_goal = goal.pause()
            self._update_goal(updated_goal)

            if goal_id in self._active_goals:
                del self._active_goals[goal_id]

            self._bus.publish(
                "goal.paused",
                {"goal_id": goal_id},
                source="goal_engine",
            )

            return updated_goal

        except ValueError as e:
            logger.error("Cannot pause goal %s: %s", goal_id, e)
            raise

    def complete(self, goal_id: str) -> Goal | None:
        """Mark a goal as completed."""
        goal = self._repository.get(goal_id)
        if not goal:
            return None

        try:
            updated_goal = goal.complete()
            self._update_goal(updated_goal)

            if goal_id in self._active_goals:
                del self._active_goals[goal_id]

            self._bus.publish(
                "goal.completed",
                {"goal_id": goal_id},
                source="goal_engine",
            )

            return updated_goal

        except ValueError as e:
            logger.error("Cannot complete goal %s: %s", goal_id, e)
            raise

    def abandon(self, goal_id: str, reason: str | None = None) -> Goal | None:
        """Abandon a goal."""
        goal = self._repository.get(goal_id)
        if not goal:
            return None

        try:
            updated_goal = goal.abandon()
            self._update_goal(updated_goal)

            if goal_id in self._active_goals:
                del self._active_goals[goal_id]

            self._bus.publish(
                "goal.abandoned",
                {"goal_id": goal_id, "reason": reason},
                source="goal_engine",
            )

            return updated_goal

        except ValueError as e:
            logger.error("Cannot abandon goal %s: %s", goal_id, e)
            raise

    def block(self, goal_id: str) -> Goal | None:
        """Block a goal."""
        goal = self._repository.get(goal_id)
        if not goal:
            return None

        try:
            updated_goal = goal.block()
            self._update_goal(updated_goal)

            self._bus.publish(
                "goal.blocked",
                {"goal_id": goal_id},
                source="goal_engine",
            )

            return updated_goal

        except ValueError as e:
            logger.error("Cannot block goal %s: %s", goal_id, e)
            raise

    # ============ Goal Hierarchy ============

    def get_child_goals(self, goal_id: str) -> list[Goal]:
        """Get all direct child goals."""
        return self._repository.get_children(goal_id)

    def get_root_goals(self) -> list[Goal]:
        """Get all top-level goals (no parent)."""
        return self._repository.get_root_goals()

    def get_goal_ancestry(self, goal_id: str) -> list[Goal]:
        """Get the ancestry chain from root to goal."""
        ancestry: list[Goal] = []
        current = self._repository.get(goal_id)

        while current:
            ancestry.insert(0, current)
            if current.parent_goal_id:
                current = self._repository.get(current.parent_goal_id)
            else:
                current = None

        return ancestry

    # ============ Persistence ============

    def _update_goal(self, goal: Goal) -> None:
        """Update goal in repository and cache."""
        self._repository.save(goal)
        self._active_goals[goal.id] = goal


class GoalEngineRepository:
    """Abstract repository interface for goals."""

    def save(self, goal: Goal) -> None:
        """Save a goal."""
        raise NotImplementedError

    def get(self, goal_id: str) -> Goal | None:
        """Get a goal by ID."""
        raise NotImplementedError

    def get_by_status(self, status: GoalStatus) -> list[Goal]:
        """Get all goals with a specific status."""
        raise NotImplementedError

    def get_active(self) -> list[Goal]:
        """Get all active goals."""
        raise NotImplementedError

    def get_children(self, goal_id: str) -> list[Goal]:
        """Get all direct child goals."""
        raise NotImplementedError

    def get_root_goals(self) -> list[Goal]:
        """Get all root goals (no parent)."""
        raise NotImplementedError

    def delete(self, goal_id: str) -> bool:
        """Delete a goal. Returns True if deleted."""
        raise NotImplementedError


class InMemoryGoalRepository(GoalEngineRepository):
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}

    def save(self, goal: Goal) -> None:
        self._goals[goal.id] = goal

    def get(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def get_by_status(self, status: GoalStatus) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == status]

    def get_active(self) -> list[Goal]:
        return [g for g in self._goals.values() if not g.status.is_terminal]

    def get_children(self, goal_id: str) -> list[Goal]:
        return [g for g in self._goals.values() if g.parent_goal_id == goal_id]

    def get_root_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.parent_goal_id is None]

    def delete(self, goal_id: str) -> bool:
        if goal_id in self._goals:
            del self._goals[goal_id]
            return True
        return False


__all__ = ["GoalEngine", "GoalEngineRepository", "InMemoryGoalRepository"]
