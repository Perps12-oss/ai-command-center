"""Agents package — multi-agent coordination.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.3
"""

from ai_command_center.orchestration.agents.agent_coordinator import (
    AgentAssignment,
    AgentCoordinator,
)
from ai_command_center.orchestration.agents.agent_contract import (
    Agent,
    AgentCapability,
    AgentContract,
    AgentType,
)
from ai_command_center.orchestration.agents.agent_registry import (
    AgentRegistry,
    InMemoryAgentRegistry,
)

__all__ = [
    "Agent",
    "AgentAssignment",
    "AgentCapability",
    "AgentContract",
    "AgentCoordinator",
    "AgentRegistry",
    "AgentType",
    "InMemoryAgentRegistry",
]
