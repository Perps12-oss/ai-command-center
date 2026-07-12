"""Tests for Goal."""

import pytest

from ai_command_center.orchestration.goals.goal import Goal
from ai_command_center.orchestration.goals.goal_status import GoalStatus


class TestGoal:
    """Tests for Goal dataclass."""

    def test_create_goal(self):
        """Goals are created with DRAFT status by default."""
        goal = Goal(
            id="test-1",
            title="Test Goal",
            description="A test goal",
        )
        assert goal.id == "test-1"
        assert goal.title == "Test Goal"
        assert goal.status == GoalStatus.DRAFT
        assert goal.parent_goal_id is None

    def test_activate_goal(self):
        """activate() transitions from DRAFT to ACTIVE."""
        goal = Goal(id="test-1", title="Test", description="")
        activated = goal.activate()
        assert activated.status == GoalStatus.ACTIVE
        assert goal.status == GoalStatus.DRAFT  # Original unchanged

    def test_complete_goal(self):
        """complete() transitions from ACTIVE to COMPLETED."""
        goal = Goal(id="test-1", title="Test", description="", status=GoalStatus.ACTIVE)
        completed = goal.complete()
        assert completed.status == GoalStatus.COMPLETED

    def test_invalid_transition_raises(self):
        """Invalid transitions raise ValueError."""
        goal = Goal(id="test-1", title="Test", description="", status=GoalStatus.DRAFT)
        with pytest.raises(ValueError):
            goal.complete()  # Cannot go from DRAFT to COMPLETED

    def test_is_root_goal(self):
        """is_root_goal returns True for top-level goals."""
        root = Goal(id="root", title="Root", description="")
        child = Goal(id="child", title="Child", description="", parent_goal_id="root")
        assert root.is_root_goal
        assert not child.is_root_goal

    def test_immutability(self):
        """Goal methods return new instances."""
        goal = Goal(id="test-1", title="Test", description="")
        activated = goal.activate()
        assert goal is not activated
        assert goal.status == GoalStatus.DRAFT
        assert activated.status == GoalStatus.ACTIVE

    def test_with_priority(self):
        """with_priority() returns new instance with updated priority."""
        goal = Goal(id="test-1", title="Test", description="", priority=0)
        updated = goal.with_priority(10)
        assert updated.priority == 10
        assert goal.priority == 0

    def test_with_tags(self):
        """with_tags() returns new instance with updated tags."""
        goal = Goal(id="test-1", title="Test", description="", tags=[])
        updated = goal.with_tags(["tag1", "tag2"])
        assert updated.tags == ["tag1", "tag2"]
        assert goal.tags == []
