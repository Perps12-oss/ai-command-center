"""Tests for AgentRegistry."""

import pytest

from ai_command_center.orchestration.agents.agent_contract import (
    AgentStatus,
    AgentType,
    OPERATOR_CONTRACT,
    PLANNER_CONTRACT,
)
from ai_command_center.orchestration.agents.agent_registry import (
    AgentRegistry,
    InMemoryAgentRegistry,
)


@pytest.fixture
def registry():
    """Create an in-memory registry."""
    return InMemoryAgentRegistry()


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def test_spawn_agent(self, registry):
        """spawn_agent creates a new agent."""
        agent = registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        assert agent.id == "op-1"
        assert agent.contract == OPERATOR_CONTRACT
        assert agent.status == AgentStatus.IDLE

    def test_spawn_agent_generates_id(self, registry):
        """spawn_agent generates ID if not provided."""
        agent = registry.spawn_agent(OPERATOR_CONTRACT)
        assert agent.id.startswith("agent-")

    def test_get_agent(self, registry):
        """get_agent returns spawned agent."""
        spawned = registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        retrieved = registry.get_agent("op-1")
        assert retrieved is spawned

    def test_get_agent_not_found(self, registry):
        """get_agent returns None for unknown ID."""
        assert registry.get_agent("nonexistent") is None

    def test_list_agents(self, registry):
        """list_agents returns all spawned agents."""
        registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        registry.spawn_agent(PLANNER_CONTRACT, agent_id="pl-1")
        agents = registry.list_agents()
        assert len(agents) == 2

    def test_list_agents_filter_by_status(self, registry):
        """list_agents can filter by status."""
        agent1 = registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        agent2 = registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-2")

        # Update agent2 to BUSY
        registry.update_agent(agent2.assign_task("task-1"))

        idle = registry.list_agents(status=AgentStatus.IDLE)
        busy = registry.list_agents(status=AgentStatus.BUSY)

        assert len(idle) == 1
        assert idle[0].id == "op-1"
        assert len(busy) == 1
        assert busy[0].id == "op-2"

    def test_list_agents_filter_by_type(self, registry):
        """list_agents can filter by agent type."""
        registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        registry.spawn_agent(PLANNER_CONTRACT, agent_id="pl-1")

        operators = registry.list_agents(agent_type=AgentType.OPERATOR)
        planners = registry.list_agents(agent_type=AgentType.PLANNER)

        assert len(operators) == 1
        assert operators[0].id == "op-1"
        assert len(planners) == 1
        assert planners[0].id == "pl-1"

    def test_get_available_agents(self, registry):
        """get_available_agents returns idle agents."""
        agent1 = registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        agent2 = registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-2")

        # Assign agent1 to a task
        registry.update_agent(agent1.assign_task("task-1"))

        available = registry.get_available_agents()
        assert len(available) == 1
        assert available[0].id == "op-2"

    def test_get_available_agents_with_capability(self, registry):
        """get_available_agents filters by capability."""
        registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        registry.spawn_agent(PLANNER_CONTRACT, agent_id="pl-1")

        with_execute = registry.get_available_agents(capability="command.execute")
        with_decompose = registry.get_available_agents(capability="goal.decompose")

        assert len(with_execute) == 1  # Only operator has command.execute
        assert len(with_decompose) == 1  # Only planner has goal.decompose

    def test_update_agent(self, registry):
        """update_agent changes agent state."""
        agent = registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        updated = agent.assign_task("task-1")
        registry.update_agent(updated)

        retrieved = registry.get_agent("op-1")
        assert retrieved.status == AgentStatus.BUSY
        assert retrieved.current_task_id == "task-1"

    def test_terminate_agent(self, registry):
        """terminate_agent sets agent to TERMINATED."""
        registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        result = registry.terminate_agent("op-1")

        assert result is True
        agent = registry.get_agent("op-1")
        assert agent.status == AgentStatus.TERMINATED

    def test_terminate_nonexistent(self, registry):
        """terminate_agent returns False for unknown ID."""
        result = registry.terminate_agent("nonexistent")
        assert result is False

    def test_active_count(self, registry):
        """active_count returns non-terminated agents."""
        registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-2")
        registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-3")

        registry.terminate_agent("op-1")

        assert registry.active_count == 2

    def test_idle_count(self, registry):
        """idle_count returns idle agents."""
        agent1 = registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-1")
        registry.spawn_agent(OPERATOR_CONTRACT, agent_id="op-2")

        # Assign agent1
        registry.update_agent(agent1.assign_task("task-1"))

        assert registry.idle_count == 1
