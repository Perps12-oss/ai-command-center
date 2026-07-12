"""PlanningEngine — generates execution plans from goals.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.2
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ai_command_center.orchestration.goals.goal import Goal
from ai_command_center.orchestration.goals.task import Task, TaskPriority
from ai_command_center.orchestration.goals.task_graph import TaskGraph

logger = logging.getLogger(__name__)


class PlanStatus(str, Enum):
    """Lifecycle states for an ExecutionPlan."""

    DRAFT = "draft"  # Plan created, not validated
    VALIDATED = "validated"  # Plan passes all checks
    APPROVED = "approved"  # User approved the plan
    REJECTED = "rejected"  # User rejected the plan
    EXECUTING = "executing"  # Plan is being executed
    COMPLETED = "completed"  # All tasks completed successfully
    FAILED = "failed"  # Plan execution failed
    CANCELLED = "cancelled"  # Plan was cancelled


@dataclass
class ExecutionPlan:
    """A plan for executing a goal.

    The ExecutionPlan contains a TaskGraph that defines what tasks
    need to be done and their dependencies.
    """

    id: str
    goal_id: str
    title: str
    description: str = ""
    status: PlanStatus = PlanStatus.DRAFT
    task_graph: TaskGraph | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "planner"
    approved_by: str | None = None
    estimated_duration: int | None = None  # seconds
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate the plan."""
        if not self.task_graph:
            return False
        if not self.task_graph.tasks:
            return False
        return True

    def get_execution_order(self) -> list[list[str]]:
        """Get task execution order for parallel execution."""
        if not self.task_graph:
            return []
        return self.task_graph.get_execution_order()

    @property
    def completion_percentage(self) -> float:
        """Get the percentage of tasks completed."""
        if not self.task_graph:
            return 0.0
        return self.task_graph.completion_percentage


class PlanningStage(str, Enum):
    """Stages in the planning pipeline."""

    EXPLORE = "explore"  # Understand context
    PLAN = "plan"  # Generate task graph
    VALIDATE = "validate"  # Verify plan correctness
    APPROVE = "approve"  # User approval
    EXECUTE = "execute"  # Execute tasks


@dataclass
class PlanningContext:
    """Context gathered during the Explore stage."""

    workspace_state: dict[str, Any] = field(default_factory=dict)
    relevant_files: list[str] = field(default_factory=list)
    existing_goals: list[str] = field(default_factory=list)
    available_capabilities: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


class PlanningEngine:
    """Generates ExecutionPlans from Goals.

    The planning pipeline has four stages:
    1. EXPLORE: Gather context about the workspace and constraints
    2. PLAN: Generate a TaskGraph with tasks and dependencies
    3. VALIDATE: Verify the plan is correct and complete
    4. APPROVE: Get user approval for high-risk plans

    The engine publishes events at each stage and can be extended
    with custom planners for specific goal types.
    """

    def __init__(
        self,
        planner_registry: PlannerRegistry | None = None,
    ) -> None:
        self._planner_registry = planner_registry or PlannerRegistry()

    def create_plan(self, goal: Goal) -> ExecutionPlan:
        """Create an execution plan for a goal.

        This runs the full planning pipeline:
        1. Explore context
        2. Generate tasks
        3. Build task graph
        4. Validate plan

        Args:
            goal: The goal to plan for

        Returns:
            A validated ExecutionPlan
        """
        logger.info("Creating plan for goal: %s", goal.id)

        # Stage 1: Explore
        context = self._explore(goal)
        self._publish_stage(PlanningStage.EXPLORE, goal.id, context)

        # Stage 2: Plan
        tasks = self._generate_tasks(goal, context)
        task_graph = self._build_task_graph(goal.id, tasks)
        self._publish_stage(PlanningStage.PLAN, goal.id, {"task_count": len(tasks)})

        # Stage 3: Validate
        plan = ExecutionPlan(
            id=f"plan-{goal.id}",
            goal_id=goal.id,
            title=f"Plan for: {goal.title}",
            description=f"Execution plan generated for goal: {goal.description}",
            task_graph=task_graph,
        )

        if plan.validate():
            plan.status = PlanStatus.VALIDATED

        self._publish_stage(PlanningStage.VALIDATE, goal.id, {"valid": plan.validate()})

        return plan

    def _explore(self, goal: Goal) -> PlanningContext:
        """Explore stage: gather context.

        This is a placeholder for actual context gathering.
        In production, this would query the WorldModel, workspace,
        and other services for relevant information.
        """
        return PlanningContext(
            constraints=["Minimize side effects"],
            risks=["May require user confirmation for destructive actions"],
        )

    def _generate_tasks(self, goal: Goal, context: PlanningContext) -> list[Task]:
        """Generate tasks for the goal.

        This uses a registered planner or the default implementation.
        """
        planner = self._planner_registry.get_planner(goal.id)
        if planner:
            return planner.generate_tasks(goal, context)

        # Default: create a single task for the goal
        return [
            Task(
                id=f"task-{goal.id}-1",
                goal_id=goal.id,
                title=goal.title,
                description=goal.description,
                priority=TaskPriority.NORMAL,
            )
        ]

    def _build_task_graph(
        self,
        goal_id: str,
        tasks: list[Task],
    ) -> TaskGraph:
        """Build a TaskGraph from a list of tasks."""
        graph = TaskGraph(goal_id=goal_id)

        for task in tasks:
            graph = graph.add_task(task)

        # In a full implementation, this would analyze tasks and add
        # dependencies based on their content and constraints

        return graph

    def _publish_stage(
        self,
        stage: PlanningStage,
        goal_id: str,
        data: dict[str, Any],
    ) -> None:
        """Publish planning stage event."""
        logger.debug("Planning stage %s for goal %s: %s", stage.value, goal_id, data)


class PlannerRegistry:
    """Registry for domain-specific planners."""

    def __init__(self) -> None:
        self._planners: dict[str, GoalPlanner] = {}

    def register(self, goal_pattern: str, planner: GoalPlanner) -> None:
        """Register a planner for a goal pattern.

        Args:
            goal_pattern: A pattern to match goal IDs against
            planner: The planner to use
        """
        self._planners[goal_pattern] = planner

    def get_planner(self, goal_id: str) -> GoalPlanner | None:
        """Get a planner for a goal ID.

        Returns the first planner whose pattern matches the goal ID.
        """
        for pattern, planner in self._planners.items():
            if pattern in goal_id or goal_id.startswith(pattern):
                return planner
        return None


class GoalPlanner:
    """Abstract base for domain-specific planners."""

    def generate_tasks(
        self,
        goal: Goal,
        context: PlanningContext,
    ) -> list[Task]:
        """Generate tasks for achieving the goal.

        Args:
            goal: The goal to plan for
            context: Context gathered during Explore stage

        Returns:
            A list of Tasks to be executed
        """
        raise NotImplementedError


__all__ = [
    "ExecutionPlan",
    "GoalPlanner",
    "PlanStatus",
    "PlanningContext",
    "PlanningEngine",
    "PlanningStage",
    "PlannerRegistry",
]
