"""AgentRegistry — manages agent instances.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.3
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from ai_command_center.orchestration.agents.agent_contract import (
    Agent,
    AgentContract,
    AgentStatus,
    AgentType,
)

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing agent instances.

    The AgentRegistry:
    - Spawns new agents from contracts
    - Tracks active agents
    - Routes task assignments to available agents
    - Handles agent termination
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus
        self._agents: dict[str, Agent] = {}

    def spawn_agent(
        self,
        contract: AgentContract,
        agent_id: str | None = None,
    ) -> Agent:
        """Spawn a new agent from a contract.

        Args:
            contract: The agent contract defining capabilities
            agent_id: Optional ID (generated if not provided)

        Returns:
            The newly created Agent
        """
        agent = Agent(
            id=agent_id or f"agent-{uuid.uuid4().hex[:8]}",
            contract=contract,
            status=AgentStatus.IDLE,
        )

        self._agents[agent.id] = agent
        logger.info("Spawned agent: %s (%s)", agent.id, contract.name)

        if self._bus:
            self._bus.publish(
                "agent.spawned",
                {
                    "agent_id": agent.id,
                    "agent_type": contract.agent_type.value,
                    "name": contract.name,
                },
                source="agent_registry",
            )

        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(
        self,
        status: AgentStatus | None = None,
        agent_type: AgentType | None = None,
    ) -> list[Agent]:
        """List agents, optionally filtered.

        Args:
            status: Filter by agent status
            agent_type: Filter by agent type

        Returns:
            List of matching agents
        """
        agents = list(self._agents.values())

        if status is not None:
            agents = [a for a in agents if a.status == status]

        if agent_type is not None:
            agents = [a for a in agents if a.contract.agent_type == agent_type]

        return agents

    def get_available_agents(
        self,
        capability: str | None = None,
        agent_type: AgentType | None = None,
    ) -> list[Agent]:
        """Get all available (idle) agents.

        Args:
            capability: Filter to agents with this capability
            agent_type: Filter by agent type

        Returns:
            List of available agents
        """
        agents = self.list_agents(status=AgentStatus.IDLE)

        if agent_type is not None:
            agents = [a for a in agents if a.contract.agent_type == agent_type]

        if capability:
            agents = [a for a in agents if a.contract.has_capability(capability)]

        return agents

    def update_agent(self, agent: Agent) -> None:
        """Update an agent's state."""
        self._agents[agent.id] = agent

        if self._bus:
            self._bus.publish(
                "agent.updated",
                {
                    "agent_id": agent.id,
                    "status": agent.status.value,
                },
                source="agent_registry",
            )

    def terminate_agent(self, agent_id: str) -> bool:
        """Terminate an agent.

        Returns True if terminated, False if not found.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        terminated_agent = agent.terminate()
        self._agents[agent_id] = terminated_agent

        logger.info("Terminated agent: %s", agent_id)

        if self._bus:
            self._bus.publish(
                "agent.terminated",
                {"agent_id": agent_id},
                source="agent_registry",
            )

        return True

    @property
    def active_count(self) -> int:
        """Get count of active (non-terminated) agents."""
        return sum(1 for a in self._agents.values() if a.status != AgentStatus.TERMINATED)

    @property
    def idle_count(self) -> int:
        """Get count of idle agents."""
        return sum(1 for a in self._agents.values() if a.status == AgentStatus.IDLE)


class InMemoryAgentRegistry(AgentRegistry):
    """In-memory agent registry for testing."""

    def __init__(self) -> None:
        # Skip EventBus for in-memory version
        super().__init__(bus=None)


__all__ = ["AgentRegistry", "InMemoryAgentRegistry"]
