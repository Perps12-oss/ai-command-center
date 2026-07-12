"""PredictiveEngine — predicts blockers and opportunities based on world model state.

Reference: docs/plans/PHASE_10_WORLD_MODEL_PLAN.md Section 10.4
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PredictionType(str, Enum):
    """Types of predictions."""

    BLOCKER = "blocker"  # Something that will block progress
    OPPORTUNITY = "opportunity"  # Something that could improve outcomes
    RISK = "risk"  # Potential issue that needs attention
    RECOMMENDATION = "recommendation"  # Suggested action


class RiskLevel(str, Enum):
    """Risk levels for predictions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Prediction:
    """A prediction about future state based on current world model."""

    id: str = ""
    type: PredictionType = PredictionType.BLOCKER
    title: str = ""
    description: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    affected_entity_ids: list[str] = field(default_factory=list)
    affected_goal_ids: list[str] = field(default_factory=list)
    affected_task_ids: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    confidence: float = 0.5  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_blocker(self) -> bool:
        """Return True if this is a blocker prediction."""
        return self.type == PredictionType.BLOCKER

    def is_high_risk(self) -> bool:
        """Return True if risk level is high or critical."""
        return self.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}


@dataclass
class BlockerPrediction(Prediction):
    """A prediction about something that will block progress."""

    id: str = ""
    title: str = ""
    description: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    blocker_type: str = "dependency"  # dependency, resource, external, etc.
    estimated_delay_hours: float | None = None
    type: PredictionType = PredictionType.BLOCKER


@dataclass
class OpportunityPrediction(Prediction):
    """A prediction about something that could improve outcomes."""

    id: str = ""
    title: str = ""
    description: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    estimated_impact: str | None = None  # e.g., "2x faster", "50% less effort"
    type: PredictionType = PredictionType.OPPORTUNITY


class PredictiveEngine:
    """Predicts blockers and opportunities from world model state.

    The PredictiveEngine analyzes:
    - Goal dependencies and their status
    - Task completion rates and trends
    - Resource availability and conflicts
    - External factors and deadlines

    It publishes predictions to the EventBus for the Operator to act on.
    """

    def __init__(
        self,
        goal_analyzer: GoalAnalyzer | None = None,
        task_analyzer: TaskAnalyzer | None = None,
    ) -> None:
        self._goal_analyzer = goal_analyzer or GoalAnalyzer()
        self._task_analyzer = task_analyzer or TaskAnalyzer()
        self._prediction_history: list[Prediction] = []

    def analyze_goals(self, goals: list[Any]) -> list[Prediction]:
        """Analyze goals and predict blockers/opportunities.

        Args:
            goals: List of Goal objects to analyze

        Returns:
            List of predictions about the goals
        """
        predictions: list[Prediction] = []

        for goal in goals:
            # Check for blocked goals
            if hasattr(goal, 'status'):
                from ai_command_center.orchestration.goals.goal_status import GoalStatus
                if goal.status == GoalStatus.BLOCKED:
                    blocker = self._create_blocker_prediction(
                        goal=goal,
                        title=f"Goal blocked: {goal.title}",
                        description="Goal is waiting on dependencies or resources",
                        blocker_type="dependency",
                    )
                    predictions.append(blocker)

                # Check for overdue goals
                if hasattr(goal, 'deadline') and goal.deadline:
                    if goal.deadline < datetime.utcnow():
                        risk = self._create_blocker_prediction(
                            goal=goal,
                            title=f"Goal overdue: {goal.title}",
                            description="Goal deadline has passed",
                            blocker_type="deadline",
                            risk_level=RiskLevel.HIGH,
                        )
                        predictions.append(risk)

            # Check for hierarchical issues
            if hasattr(goal, 'parent_goal_id') and goal.parent_goal_id:
                # This is a sub-goal - check if parent might be affected
                pass  # Implementation would check parent status

        return predictions

    def analyze_tasks(self, tasks: list[Any]) -> list[Prediction]:
        """Analyze tasks and predict blockers/opportunities.

        Args:
            tasks: List of Task objects to analyze

        Returns:
            List of predictions about the tasks
        """
        predictions: list[Prediction] = []

        for task in tasks:
            # Check for blocked tasks
            if hasattr(task, 'status'):
                from ai_command_center.orchestration.goals.task import TaskStatus
                if task.status == TaskStatus.BLOCKED:
                    blocker = self._create_blocker_prediction(
                        task=task,
                        title=f"Task blocked: {task.title}",
                        description="Task is waiting on dependencies",
                        blocker_type="dependency",
                    )
                    predictions.append(blocker)

                # Check for failed tasks that exceeded retries
                if hasattr(task, 'has_failed_permanently') and task.has_failed_permanently:
                    blocker = self._create_blocker_prediction(
                        task=task,
                        title=f"Task permanently failed: {task.title}",
                        description="Task has exceeded maximum retries",
                        blocker_type="failure",
                        risk_level=RiskLevel.HIGH,
                    )
                    predictions.append(blocker)

            # Check for long-running tasks
            if hasattr(task, 'estimated_duration') and hasattr(task, 'actual_duration'):
                if task.estimated_duration and task.actual_duration:
                    if task.actual_duration > task.estimated_duration * 1.5:
                        opportunity = self._create_opportunity_prediction(
                            task=task,
                            title=f"Task taking longer than expected: {task.title}",
                            description=f"Actual: {task.actual_duration}s, Expected: {task.estimated_duration}s",
                            recommendation="Consider breaking this task into smaller units",
                        )
                        predictions.append(opportunity)

        return predictions

    def analyze_relationships(
        self,
        entities: dict[str, Any],
        relationships: list[Any],
    ) -> list[Prediction]:
        """Analyze entity relationships for potential issues.

        Args:
            entities: Dict of entity_id -> entity
            relationships: List of relationship objects

        Returns:
            List of predictions about relationships
        """
        predictions: list[Prediction] = []

        # Check for circular dependencies
        # This would require analyzing the dependency graph
        # For now, we'll add a placeholder

        return predictions

    def get_all_predictions(
        self,
        goals: list[Any] | None = None,
        tasks: list[Any] | None = None,
    ) -> list[Prediction]:
        """Get all predictions from analyzing goals and tasks.

        Args:
            goals: Optional list of goals to analyze
            tasks: Optional list of tasks to analyze

        Returns:
            Combined list of all predictions
        """
        predictions: list[Prediction] = []

        if goals:
            predictions.extend(self.analyze_goals(goals))

        if tasks:
            predictions.extend(self.analyze_tasks(tasks))

        # Sort by risk level and confidence
        predictions.sort(
            key=lambda p: (
                self._risk_priority(p.risk_level),
                -p.confidence,
            ),
            reverse=True,
        )

        # Store in history
        self._prediction_history.extend(predictions)

        return predictions

    def get_blockers(self) -> list[BlockerPrediction]:
        """Get all current blockers."""
        return [
            p for p in self._prediction_history
            if isinstance(p, BlockerPrediction)
        ]

    def get_opportunities(self) -> list[OpportunityPrediction]:
        """Get all current opportunities."""
        return [
            p for p in self._prediction_history
            if isinstance(p, OpportunityPrediction)
        ]

    def clear_resolved(self, resolved_ids: list[str]) -> None:
        """Remove resolved predictions from history.

        Args:
            resolved_ids: IDs of predictions that have been resolved
        """
        self._prediction_history = [
            p for p in self._prediction_history
            if p.id not in resolved_ids
        ]

    def _create_blocker_prediction(
        self,
        goal: Any | None = None,
        task: Any | None = None,
        title: str = "",
        description: str = "",
        blocker_type: str = "dependency",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> BlockerPrediction:
        """Create a blocker prediction."""
        import uuid

        affected_goals = [goal.id] if goal else []
        affected_tasks = [task.id] if task else []

        return BlockerPrediction(
            id=str(uuid.uuid4()),
            type=PredictionType.BLOCKER,
            title=title,
            description=description,
            risk_level=risk_level,
            affected_entity_ids=[],
            affected_goal_ids=affected_goals,
            affected_task_ids=affected_tasks,
            blocker_type=blocker_type,
        )

    def _create_opportunity_prediction(
        self,
        goal: Any | None = None,
        task: Any | None = None,
        title: str = "",
        description: str = "",
        recommendation: str = "",
    ) -> OpportunityPrediction:
        """Create an opportunity prediction."""
        import uuid

        affected_goals = [goal.id] if goal else []
        affected_tasks = [task.id] if task else []

        return OpportunityPrediction(
            id=str(uuid.uuid4()),
            type=PredictionType.OPPORTUNITY,
            title=title,
            description=description,
            risk_level=RiskLevel.LOW,
            affected_entity_ids=[],
            affected_goal_ids=affected_goals,
            affected_task_ids=affected_tasks,
            suggested_actions=[recommendation] if recommendation else [],
        )

    def _risk_priority(self, risk_level: RiskLevel) -> int:
        """Convert risk level to priority number."""
        priorities = {
            RiskLevel.CRITICAL: 4,
            RiskLevel.HIGH: 3,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 1,
        }
        return priorities.get(risk_level, 0)


class GoalAnalyzer:
    """Analyzes goal patterns for predictions."""

    def find_blocked_subtree(self, goals: list[Any]) -> list[str]:
        """Find goals that are blocked by other blocked goals."""
        blocked_ids: list[str] = []
        for goal in goals:
            if hasattr(goal, 'parent_goal_id') and goal.parent_goal_id in blocked_ids:
                blocked_ids.append(goal.id)
        return blocked_ids


class TaskAnalyzer:
    """Analyzes task patterns for predictions."""

    def estimate_completion_time(
        self,
        tasks: list[Any],
    ) -> float | None:
        """Estimate time to complete all tasks.

        Returns:
            Estimated hours, or None if cannot estimate
        """
        total = 0
        count = 0
        for task in tasks:
            if hasattr(task, 'estimated_duration') and task.estimated_duration:
                total += task.estimated_duration
                count += 1

        if count == 0:
            return None

        # Return hours
        return (total / count) / 3600
