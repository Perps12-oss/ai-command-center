"""Tests for PredictiveEngine."""

import pytest
from datetime import datetime, timedelta

from ai_command_center.core.world_model.predictive_engine import (
    BlockerPrediction,
    OpportunityPrediction,
    Prediction,
    PredictionType,
    PredictiveEngine,
    RiskLevel,
)
from ai_command_center.orchestration.goals.goal import Goal
from ai_command_center.orchestration.goals.goal_status import GoalStatus
from ai_command_center.orchestration.goals.task import Task, TaskStatus


class MockGoal:
    """Mock goal for testing."""

    def __init__(
        self,
        id: str = "goal-1",
        title: str = "Test Goal",
        status: GoalStatus = GoalStatus.ACTIVE,
        deadline: datetime | None = None,
        parent_goal_id: str | None = None,
    ):
        self.id = id
        self.title = title
        self.status = status
        self.deadline = deadline
        self.parent_goal_id = parent_goal_id


class MockTask:
    """Mock task for testing."""

    def __init__(
        self,
        id: str = "task-1",
        title: str = "Test Task",
        status: TaskStatus = TaskStatus.PENDING,
        estimated_duration: int | None = None,
        actual_duration: int | None = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ):
        self.id = id
        self.title = title
        self.status = status
        self.estimated_duration = estimated_duration
        self.actual_duration = actual_duration
        self.retry_count = retry_count
        self.max_retries = max_retries

    @property
    def has_failed_permanently(self) -> bool:
        return self.status == TaskStatus.FAILED and self.retry_count >= self.max_retries


class TestPrediction:
    """Tests for Prediction dataclass."""

    def test_create_prediction(self):
        """Predictions can be created with required fields."""
        pred = Prediction(
            id="pred-1",
            type=PredictionType.BLOCKER,
            title="Test blocker",
            description="A test blocker",
            risk_level=RiskLevel.HIGH,
        )
        assert pred.id == "pred-1"
        assert pred.type == PredictionType.BLOCKER
        assert pred.is_blocker()

    def test_is_high_risk(self):
        """is_high_risk returns True for high/critical levels."""
        low = Prediction(
            id="1", type=PredictionType.BLOCKER, title="", description="", risk_level=RiskLevel.LOW
        )
        high = Prediction(
            id="2", type=PredictionType.BLOCKER, title="", description="", risk_level=RiskLevel.HIGH
        )
        critical = Prediction(
            id="3", type=PredictionType.BLOCKER, title="", description="", risk_level=RiskLevel.CRITICAL
        )

        assert not low.is_high_risk()
        assert high.is_high_risk()
        assert critical.is_high_risk()


class TestBlockerPrediction:
    """Tests for BlockerPrediction."""

    def test_create_blocker(self):
        """Blocker predictions have correct type."""
        blocker = BlockerPrediction(
            id="block-1",
            title="Test",
            description="Test blocker",
            risk_level=RiskLevel.HIGH,
            blocker_type="dependency",
        )
        assert blocker.is_blocker()
        assert blocker.blocker_type == "dependency"
        assert blocker.type == PredictionType.BLOCKER


class TestOpportunityPrediction:
    """Tests for OpportunityPrediction."""

    def test_create_opportunity(self):
        """Opportunity predictions have correct type."""
        opp = OpportunityPrediction(
            id="opp-1",
            title="Test",
            description="Test opportunity",
            risk_level=RiskLevel.LOW,
        )
        assert not opp.is_blocker()
        assert opp.type == PredictionType.OPPORTUNITY


class TestPredictiveEngine:
    """Tests for PredictiveEngine."""

    def test_analyze_blocked_goal(self):
        """Blocked goals generate blocker predictions."""
        engine = PredictiveEngine()
        goals = [MockGoal(id="goal-1", status=GoalStatus.BLOCKED)]

        predictions = engine.analyze_goals(goals)

        assert len(predictions) == 1
        assert predictions[0].is_blocker()
        assert "blocked" in predictions[0].title.lower()

    def test_analyze_overdue_goal(self):
        """Overdue goals generate high-risk predictions."""
        engine = PredictiveEngine()
        past = datetime.utcnow() - timedelta(days=1)
        goals = [MockGoal(id="goal-1", deadline=past)]

        predictions = engine.analyze_goals(goals)

        assert len(predictions) == 1
        assert predictions[0].risk_level == RiskLevel.HIGH

    def test_analyze_active_goal(self):
        """Active goals don't generate predictions."""
        engine = PredictiveEngine()
        goals = [MockGoal(id="goal-1", status=GoalStatus.ACTIVE)]

        predictions = engine.analyze_goals(goals)

        assert len(predictions) == 0

    def test_analyze_blocked_task(self):
        """Blocked tasks generate blocker predictions."""
        engine = PredictiveEngine()
        tasks = [MockTask(id="task-1", status=TaskStatus.BLOCKED)]

        predictions = engine.analyze_tasks(tasks)

        assert len(predictions) == 1
        assert predictions[0].is_blocker()

    def test_analyze_failed_task(self):
        """Permanently failed tasks generate high-risk predictions."""
        engine = PredictiveEngine()
        tasks = [MockTask(
            id="task-1",
            status=TaskStatus.FAILED,
            retry_count=3,
            max_retries=3,
        )]

        predictions = engine.analyze_tasks(tasks)

        assert len(predictions) == 1
        assert predictions[0].risk_level == RiskLevel.HIGH

    def test_analyze_slow_task(self):
        """Tasks running longer than expected generate opportunities."""
        engine = PredictiveEngine()
        tasks = [MockTask(
            id="task-1",
            estimated_duration=100,
            actual_duration=200,
        )]

        predictions = engine.analyze_tasks(tasks)

        assert len(predictions) == 1
        assert not predictions[0].is_blocker()

    def test_get_all_predictions_sorted(self):
        """Predictions are sorted by risk level and confidence."""
        engine = PredictiveEngine()
        goals = [MockGoal(id="goal-1", status=GoalStatus.BLOCKED)]
        tasks = [MockTask(id="task-1", status=TaskStatus.BLOCKED)]

        predictions = engine.get_all_predictions(goals=goals, tasks=tasks)

        assert len(predictions) == 2
        # All blockers should have BLOCKER type
        assert all(p.is_blocker() for p in predictions)
        # First prediction should be a blocker
        assert predictions[0].type == PredictionType.BLOCKER

    def test_get_blockers(self):
        """get_blockers returns only blocker predictions."""
        engine = PredictiveEngine()
        goals = [MockGoal(id="goal-1", status=GoalStatus.BLOCKED)]
        engine.get_all_predictions(goals=goals)

        blockers = engine.get_blockers()

        assert len(blockers) == 1
        assert all(b.is_blocker() for b in blockers)

    def test_clear_resolved(self):
        """clear_resolved removes specified predictions."""
        engine = PredictiveEngine()
        goals = [MockGoal(id="goal-1", status=GoalStatus.BLOCKED)]
        predictions = engine.get_all_predictions(goals=goals)

        assert len(engine.get_blockers()) == 1

        engine.clear_resolved([predictions[0].id])

        assert len(engine.get_blockers()) == 0
