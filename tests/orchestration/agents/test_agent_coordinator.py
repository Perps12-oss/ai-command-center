"""Tests for AgentCoordinator."""

import pytest

from ai_command_center.orchestration.agents.agent_coordinator import (
    AgentAssignment,
    AgentCoordinator,
    CoordinationStatus,
)
from ai_command_center.orchestration.agents.agent_registry import InMemoryAgentRegistry
from ai_command_center.orchestration.goals.task import Task
from ai_command_center.orchestration.agents.agent_contract import OPERATOR_CONTRACT


@pytest.fixture
def registry():
    """Create a registry with multiple test agents."""
    reg = InMemoryAgentRegistry()
    reg.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
    reg.spawn_agent(OPERATOR_CONTRACT, agent_id="op-2")
    return reg


@pytest.fixture
def coordinator(registry):
    """Create a coordinator with the test registry."""
    return AgentCoordinator(registry)


class TestAgentCoordinator:
    """Tests for AgentCoordinator."""

    def test_assign_task(self, coordinator, registry):
        """assign_task assigns task to available agent."""
        task = Task(id="task-1", goal_id="goal-1", title="Test task")
        assignment = coordinator.assign_task(task)

        assert assignment is not None
        assert assignment.task_id == "task-1"
        assert assignment.agent_id == "op-1"

        # Verify agent state changed
        agent = registry.get_agent("op-1")
        assert agent.current_task_id == "task-1"

    def test_assign_task_no_available_agent(self):
        """assign_task returns None when no agent available."""
        # Create registry with only one agent
        reg = InMemoryAgentRegistry()
        reg.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        coordinator = AgentCoordinator(reg)

        # Assign the only agent
        task1 = Task(id="task-1", goal_id="goal-1", title="Task 1")
        coordinator.assign_task(task1)

        # Try to assign another - should fail
        task2 = Task(id="task-2", goal_id="goal-1", title="Task 2")
        assignment = coordinator.assign_task(task2)

        assert assignment is None

    def test_complete_assignment(self, coordinator):
        """complete_assignment marks task as done."""
        task = Task(id="task-1", goal_id="goal-1", title="Test task")
        coordinator.assign_task(task)

        coordinator.complete_assignment("task-1", result={"output": "success"})

        assignment = coordinator.get_assignment("task-1")
        assert assignment.is_complete
        assert assignment.is_successful
        assert assignment.result == {"output": "success"}

        # Verify agent is released
        agent = coordinator._agent_registry.get_agent("op-1")
        assert agent.status.value == "idle"
        assert agent.current_task_id is None

    def test_complete_assignment_with_error(self, coordinator):
        """complete_assignment handles errors."""
        task = Task(id="task-1", goal_id="goal-1", title="Test task")
        coordinator.assign_task(task)

        coordinator.complete_assignment("task-1", error="Something went wrong")

        assignment = coordinator.get_assignment("task-1")
        assert assignment.is_complete
        assert not assignment.is_successful
        assert assignment.error == "Something went wrong"

    def test_get_agent_for_task(self, coordinator):
        """get_agent_for_task returns assigned agent."""
        task = Task(id="task-1", goal_id="goal-1", title="Test task")
        coordinator.assign_task(task)

        agent = coordinator.get_agent_for_task("task-1")
        assert agent is not None
        assert agent.id == "op-1"

    def test_get_assignment(self, coordinator):
        """get_assignment returns assignment for task."""
        task = Task(id="task-1", goal_id="goal-1", title="Test task")
        coordinator.assign_task(task)

        assignment = coordinator.get_assignment("task-1")
        assert assignment is not None
        assert assignment.task_id == "task-1"

    def test_requires_approval(self, coordinator):
        """requires_approval returns True for high-risk capabilities."""
        task = Task(id="task-1", goal_id="goal-1", title="Test task")

        # command.execute is high-risk
        assert coordinator.requires_approval(task, "command.execute")

        # chat.respond is not
        assert not coordinator.requires_approval(task, "chat.respond")

    def test_get_assignment_stats(self, coordinator):
        """get_assignment_stats returns correct statistics."""
        task1 = Task(id="task-1", goal_id="goal-1", title="Task 1")
        task2 = Task(id="task-2", goal_id="goal-1", title="Task 2")

        coordinator.assign_task(task1)
        coordinator.assign_task(task2)

        coordinator.complete_assignment("task-1", result={"done": True})
        coordinator.complete_assignment("task-2", error="Failed")

        stats = coordinator.get_assignment_stats()
        assert stats["total_assignments"] == 2
        assert stats["completed"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 0

    def test_get_active_assignments(self, coordinator):
        """get_active_assignments returns incomplete assignments."""
        task1 = Task(id="task-1", goal_id="goal-1", title="Task 1")
        task2 = Task(id="task-2", goal_id="goal-1", title="Task 2")

        coordinator.assign_task(task1)
        coordinator.assign_task(task2)

        coordinator.complete_assignment("task-1")

        active = coordinator.get_active_assignments()
        assert len(active) == 1
        assert active[0].task_id == "task-2"


class TestAgentAssignment:
    """Tests for AgentAssignment."""

    def test_is_complete(self):
        """is_complete is True when completed_at is set."""
        from datetime import datetime

        incomplete = AgentAssignment(task_id="t1", agent_id="a1")
        assert not incomplete.is_complete

        complete = AgentAssignment(
            task_id="t1",
            agent_id="a1",
            completed_at=datetime.utcnow(),
        )
        assert complete.is_complete

    def test_is_successful(self):
        """is_successful requires no error."""
        from datetime import datetime

        success = AgentAssignment(
            task_id="t1",
            agent_id="a1",
            completed_at=datetime.utcnow(),
            result={"done": True},
        )
        assert success.is_successful

        failed = AgentAssignment(
            task_id="t1",
            agent_id="a1",
            completed_at=datetime.utcnow(),
            error="Failed",
        )
        assert not failed.is_successful
