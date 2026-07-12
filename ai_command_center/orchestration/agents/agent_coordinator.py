"""AgentCoordinator — coordinates task execution across agents.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ai_command_center.orchestration.agents.agent_contract import Agent
from ai_command_center.orchestration.agents.agent_registry import AgentRegistry
from ai_command_center.orchestration.goals.task import Task

logger = logging.getLogger(__name__)


class CoordinationStatus(str, Enum):
    """Status of the coordination process."""

    IDLE = "idle"
    COORDINATING = "coordinating"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentAssignment:
    """Records an assignment of a task to an agent."""

    task_id: str
    agent_id: str
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    @property
    def is_complete(self) -> bool:
        """Return True if assignment is complete."""
        return self.completed_at is not None

    @property
    def is_successful(self) -> bool:
        """Return True if assignment completed successfully."""
        return self.is_complete and self.error is None


class AgentCoordinator:
    """Coordinates task execution across multiple agents.

    The AgentCoordinator:
    - Assigns tasks to appropriate agents based on capabilities
    - Manages task dependencies
    - Handles approval flows for high-risk tasks
    - Tracks assignment history
    - Publishes coordination events
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
    ) -> None:
        self._agent_registry = agent_registry
        self._assignments: dict[str, AgentAssignment] = {}  # task_id -> assignment
        self._task_to_agent: dict[str, str] = {}  # task_id -> agent_id
        self._status = CoordinationStatus.IDLE

    @property
    def status(self) -> CoordinationStatus:
        """Get current coordination status."""
        return self._status

    def assign_task(
        self,
        task: Task,
        required_capability: str | None = None,
    ) -> AgentAssignment | None:
        """Assign a task to an available agent.

        Args:
            task: The task to assign
            required_capability: Required capability for the agent

        Returns:
            AgentAssignment if successful, None if no agent available
        """
        # Find an available agent with required capability
        agents = self._agent_registry.get_available_agents(
            capability=required_capability,
        )

        if not agents:
            logger.warning("No available agent for task: %s", task.id)
            return None

        # Pick the first available agent (could be smarter with scoring)
        agent = agents[0]

        # Create assignment
        assignment = AgentAssignment(
            task_id=task.id,
            agent_id=agent.id,
        )

        self._assignments[task.id] = assignment
        self._task_to_agent[task.id] = agent.id

        # Update agent state
        updated_agent = agent.assign_task(task.id)
        self._agent_registry.update_agent(updated_agent)

        logger.info("Assigned task %s to agent %s", task.id, agent.id)
        return assignment

    def complete_assignment(
        self,
        task_id: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Mark an assignment as complete.

        Args:
            task_id: The completed task
            result: Execution result
            error: Error message if failed
        """
        assignment = self._assignments.get(task_id)
        if not assignment:
            logger.warning("No assignment found for task: %s", task_id)
            return

        # Update assignment
        updated_assignment = AgentAssignment(
            task_id=assignment.task_id,
            agent_id=assignment.agent_id,
            assigned_at=assignment.assigned_at,
            completed_at=datetime.utcnow(),
            result=result,
            error=error,
        )
        self._assignments[task_id] = updated_assignment

        # Release the agent
        agent = self._agent_registry.get_agent(assignment.agent_id)
        if agent:
            updated_agent = agent.complete_task()
            self._agent_registry.update_agent(updated_agent)

        # Clear mapping
        if task_id in self._task_to_agent:
            del self._task_to_agent[task_id]

        logger.info("Completed task %s: %s", task_id, "success" if not error else f"error: {error}")

    def get_assignment(self, task_id: str) -> AgentAssignment | None:
        """Get assignment for a task."""
        return self._assignments.get(task_id)

    def get_agent_for_task(self, task_id: str) -> Agent | None:
        """Get the agent assigned to a task."""
        agent_id = self._task_to_agent.get(task_id)
        if not agent_id:
            return None
        return self._agent_registry.get_agent(agent_id)

    def requires_approval(
        self,
        task: Task,
        capability: str | None = None,
    ) -> bool:
        """Check if task assignment requires user approval.

        Args:
            task: The task to check
            capability: The capability being used

        Returns:
            True if approval is required
        """
        if not capability:
            return False

        # Check if any available agent requires approval for this capability
        agents = self._agent_registry.get_available_agents(capability=capability)
        for agent in agents:
            if agent.contract.requires_approval(capability):
                return True

        return False

    def get_pending_approvals(self) -> list[tuple[Task, str]]:
        """Get tasks awaiting approval.

        Returns:
            List of (task, capability) tuples awaiting approval
        """
        # In a full implementation, this would track pending approvals
        return []

    def get_assignment_stats(self) -> dict[str, Any]:
        """Get statistics about assignments.

        Returns:
            Dict with assignment statistics
        """
        total = len(self._assignments)
        completed = sum(1 for a in self._assignments.values() if a.is_complete)
        successful = sum(1 for a in self._assignments.values() if a.is_successful)
        failed = sum(1 for a in self._assignments.values() if a.is_complete and a.error)

        return {
            "total_assignments": total,
            "completed": completed,
            "successful": successful,
            "failed": failed,
            "pending": total - completed,
            "success_rate": (successful / completed * 100) if completed > 0 else 0,
        }

    def get_active_assignments(self) -> list[AgentAssignment]:
        """Get all active (non-complete) assignments."""
        return [a for a in self._assignments.values() if not a.is_complete]


__all__ = [
    "AgentAssignment",
    "AgentCoordinator",
    "CoordinationStatus",
]
