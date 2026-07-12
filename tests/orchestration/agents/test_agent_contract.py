"""Tests for Agent contracts."""

import pytest

from ai_command_center.orchestration.agents.agent_contract import (
    Agent,
    AgentCapability,
    AgentContract,
    AgentStatus,
    AgentType,
    OPERATOR_CONTRACT,
    PLANNER_CONTRACT,
)


class TestAgentCapability:
    """Tests for AgentCapability."""

    def test_is_high_risk_low(self):
        """Risk level < 4 is not high risk."""
        cap = AgentCapability(name="test", description="test", risk_level=3)
        assert not cap.is_high_risk()

    def test_is_high_risk_high(self):
        """Risk level >= 4 is high risk."""
        cap = AgentCapability(name="test", description="test", risk_level=4)
        assert cap.is_high_risk()


class TestAgentContract:
    """Tests for AgentContract."""

    def test_has_capability(self):
        """has_capability returns True for matching capability."""
        assert OPERATOR_CONTRACT.has_capability("command.execute")
        assert not OPERATOR_CONTRACT.has_capability("nonexistent")

    def test_requires_approval(self):
        """requires_approval returns True for high-risk capabilities."""
        assert OPERATOR_CONTRACT.requires_approval("command.execute")
        assert not OPERATOR_CONTRACT.requires_approval("chat.respond")

    def test_get_capability(self):
        """get_capability returns the matching capability."""
        cap = OPERATOR_CONTRACT.get_capability("command.execute")
        assert cap is not None
        assert cap.risk_level == 4


class TestAgent:
    """Tests for Agent."""

    def test_create_agent(self):
        """Agent is created with correct initial state."""
        agent = Agent(id="test-1", contract=OPERATOR_CONTRACT)
        assert agent.id == "test-1"
        assert agent.status == AgentStatus.INITIALIZING
        assert agent.current_task_id is None

    def test_can_accept_task(self):
        """can_accept_task returns True for idle agents."""
        agent = Agent(id="test-1", contract=OPERATOR_CONTRACT, status=AgentStatus.IDLE)
        assert agent.can_accept_task()

        busy_agent = Agent(
            id="test-2",
            contract=OPERATOR_CONTRACT,
            status=AgentStatus.BUSY,
            current_task_id="task-1",
        )
        assert not busy_agent.can_accept_task()

    def test_assign_task(self):
        """assign_task returns new agent with task assigned."""
        agent = Agent(id="test-1", contract=OPERATOR_CONTRACT, status=AgentStatus.IDLE)
        assigned = agent.assign_task("task-1")
        assert assigned.status == AgentStatus.BUSY
        assert assigned.current_task_id == "task-1"
        assert agent.current_task_id is None  # Original unchanged

    def test_complete_task(self):
        """complete_task returns agent ready for new tasks."""
        agent = Agent(
            id="test-1",
            contract=OPERATOR_CONTRACT,
            status=AgentStatus.BUSY,
            current_task_id="task-1",
        )
        completed = agent.complete_task()
        assert completed.status == AgentStatus.IDLE
        assert completed.current_task_id is None

    def test_terminate(self):
        """terminate returns agent in TERMINATED state."""
        agent = Agent(id="test-1", contract=OPERATOR_CONTRACT, status=AgentStatus.IDLE)
        terminated = agent.terminate()
        assert terminated.status == AgentStatus.TERMINATED


class TestPredefinedContracts:
    """Tests for predefined agent contracts."""

    def test_operator_contract(self):
        """OPERATOR_CONTRACT has expected capabilities."""
        assert OPERATOR_CONTRACT.agent_type == AgentType.OPERATOR
        assert len(OPERATOR_CONTRACT.capabilities) >= 5

    def test_planner_contract(self):
        """PLANNER_CONTRACT has planning capabilities."""
        assert PLANNER_CONTRACT.agent_type == AgentType.PLANNER
        assert PLANNER_CONTRACT.has_capability("goal.decompose")
