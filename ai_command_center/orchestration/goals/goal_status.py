"""GoalStatus enum — lifecycle states for goals.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.1
"""

from enum import Enum


class GoalStatus(str, Enum):
    """Lifecycle states for a Goal.

    Goals transition through these states during their lifetime:
    - DRAFT: Initial creation, not yet activated
    - ACTIVE: Goal is being worked on
    - PAUSED: Goal work is temporarily suspended
    - BLOCKED: Goal is waiting on dependencies or resources
    - COMPLETED: Goal has been successfully achieved
    - ABANDONED: Goal was intentionally cancelled
    - FAILED: Goal could not be completed due to errors
    """

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"

    def can_transition_to(self, target: "GoalStatus") -> bool:
        """Check if transition to target state is valid.

        Valid transitions:
        - DRAFT → ACTIVE
        - DRAFT → ABANDONED
        - ACTIVE → PAUSED
        - ACTIVE → BLOCKED
        - ACTIVE → COMPLETED
        - ACTIVE → FAILED
        - ACTIVE → ABANDONED
        - PAUSED → ACTIVE
        - PAUSED → ABANDONED
        - BLOCKED → ACTIVE
        - BLOCKED → ABANDONED
        """
        valid_transitions: dict[GoalStatus, frozenset[GoalStatus]] = {
            GoalStatus.DRAFT: frozenset({
                GoalStatus.ACTIVE,
                GoalStatus.ABANDONED,
            }),
            GoalStatus.ACTIVE: frozenset({
                GoalStatus.PAUSED,
                GoalStatus.BLOCKED,
                GoalStatus.COMPLETED,
                GoalStatus.FAILED,
                GoalStatus.ABANDONED,
            }),
            GoalStatus.PAUSED: frozenset({
                GoalStatus.ACTIVE,
                GoalStatus.ABANDONED,
            }),
            GoalStatus.BLOCKED: frozenset({
                GoalStatus.ACTIVE,
                GoalStatus.ABANDONED,
            }),
            GoalStatus.COMPLETED: frozenset(),  # Terminal state
            GoalStatus.FAILED: frozenset(),  # Terminal state
            GoalStatus.ABANDONED: frozenset(),  # Terminal state
        }

        return target in valid_transitions.get(self, frozenset())

    @property
    def is_terminal(self) -> bool:
        """Return True if this is a terminal state."""
        return self in {
            GoalStatus.COMPLETED,
            GoalStatus.FAILED,
            GoalStatus.ABANDONED,
        }

    @property
    def is_active(self) -> bool:
        """Return True if goal is being actively worked on."""
        return self == GoalStatus.ACTIVE

    @property
    def is_blocked(self) -> bool:
        """Return True if goal is blocked."""
        return self == GoalStatus.BLOCKED


__all__ = ["GoalStatus"]
