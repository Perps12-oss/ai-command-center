"""Tests for GoalStatus."""

import pytest

from ai_command_center.orchestration.goals.goal_status import GoalStatus


class TestGoalStatus:
    """Tests for GoalStatus enum."""

    def test_draft_transitions(self):
        """DRAFT can transition to ACTIVE or ABANDONED."""
        assert GoalStatus.DRAFT.can_transition_to(GoalStatus.ACTIVE)
        assert GoalStatus.DRAFT.can_transition_to(GoalStatus.ABANDONED)
        assert not GoalStatus.DRAFT.can_transition_to(GoalStatus.COMPLETED)
        assert not GoalStatus.DRAFT.can_transition_to(GoalStatus.PAUSED)

    def test_active_transitions(self):
        """ACTIVE can transition to PAUSED, BLOCKED, COMPLETED, FAILED, or ABANDONED."""
        assert GoalStatus.ACTIVE.can_transition_to(GoalStatus.PAUSED)
        assert GoalStatus.ACTIVE.can_transition_to(GoalStatus.BLOCKED)
        assert GoalStatus.ACTIVE.can_transition_to(GoalStatus.COMPLETED)
        assert GoalStatus.ACTIVE.can_transition_to(GoalStatus.FAILED)
        assert GoalStatus.ACTIVE.can_transition_to(GoalStatus.ABANDONED)
        assert not GoalStatus.ACTIVE.can_transition_to(GoalStatus.DRAFT)

    def test_paused_transitions(self):
        """PAUSED can transition to ACTIVE or ABANDONED."""
        assert GoalStatus.PAUSED.can_transition_to(GoalStatus.ACTIVE)
        assert GoalStatus.PAUSED.can_transition_to(GoalStatus.ABANDONED)
        assert not GoalStatus.PAUSED.can_transition_to(GoalStatus.COMPLETED)

    def test_blocked_transitions(self):
        """BLOCKED can transition to ACTIVE or ABANDONED."""
        assert GoalStatus.BLOCKED.can_transition_to(GoalStatus.ACTIVE)
        assert GoalStatus.BLOCKED.can_transition_to(GoalStatus.ABANDONED)
        assert not GoalStatus.BLOCKED.can_transition_to(GoalStatus.COMPLETED)

    def test_terminal_states(self):
        """COMPLETED, FAILED, ABANDONED are terminal."""
        assert GoalStatus.COMPLETED.is_terminal
        assert GoalStatus.FAILED.is_terminal
        assert GoalStatus.ABANDONED.is_terminal
        assert not GoalStatus.ACTIVE.is_terminal
        assert not GoalStatus.PAUSED.is_terminal

    def test_active_property(self):
        """Only ACTIVE is considered active."""
        assert GoalStatus.ACTIVE.is_active
        assert not GoalStatus.DRAFT.is_active
        assert not GoalStatus.PAUSED.is_active
        assert not GoalStatus.BLOCKED.is_active
