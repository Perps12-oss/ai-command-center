"""Agent model and contracts.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentType(str, Enum):
    """Types of agents in the system."""

    OPERATOR = "operator"  # Main user-facing operator
    PLANNER = "planner"  # Specialized in planning
    CODER = "coder"  # Specialized in code tasks
    RESEARCHER = "researcher"  # Specialized in investigation
    REVIEWER = "reviewer"  # Specialized in code review
    ORCHESTRATOR = "orchestrator"  # Coordinates other agents
    SPECIALIST = "specialist"  # Domain-specific specialist


class AgentStatus(str, Enum):
    """Lifecycle states for an Agent."""

    INITIALIZING = "initializing"
    IDLE = "idle"  # Ready for work
    BUSY = "busy"  # Working on a task
    WAITING = "waiting"  # Waiting for dependencies
    TERMINATED = "terminated"


@dataclass
class AgentCapability:
    """A capability that an agent can perform."""

    name: str  # e.g., "code.write", "file.read", "shell.execute"
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_level: int = 1  # 1-5 scale, 5 being highest risk

    def is_high_risk(self) -> bool:
        """Return True if capability is high risk (requires approval)."""
        return self.risk_level >= 4


@dataclass
class AgentContract:
    """A contract declaring an agent's capabilities and constraints."""

    agent_type: AgentType
    name: str
    description: str
    capabilities: list[AgentCapability] = field(default_factory=list)
    max_concurrent_tasks: int = 1
    timeout_seconds: int = 300
    memory_limit_mb: int | None = None

    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability."""
        return any(cap.name == capability for cap in self.capabilities)

    def requires_approval(self, capability: str) -> bool:
        """Check if a capability requires user approval."""
        for cap in self.capabilities:
            if cap.name == capability:
                return cap.is_high_risk()
        return False

    def get_capability(self, name: str) -> AgentCapability | None:
        """Get a specific capability by name."""
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None


@dataclass
class Agent:
    """A running agent instance.

    This represents an actual agent that can execute tasks.
    It has a contract defining what it can do and current state.
    """

    id: str
    contract: AgentContract
    status: AgentStatus = AgentStatus.INITIALIZING
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: datetime = field(default_factory=datetime.utcnow)
    current_task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_accept_task(self) -> bool:
        """Return True if agent can accept a new task."""
        return (
            self.status == AgentStatus.IDLE
            and self.current_task_id is None
        )

    def is_available(self) -> bool:
        """Return True if agent is available for work."""
        return self.status in {AgentStatus.IDLE, AgentStatus.WAITING}

    def assign_task(self, task_id: str) -> Agent:
        """Return a new Agent assigned to the task."""
        return Agent(
            id=self.id,
            contract=self.contract,
            status=AgentStatus.BUSY,
            created_at=self.created_at,
            last_active_at=datetime.utcnow(),
            current_task_id=task_id,
            metadata=self.metadata,
        )

    def complete_task(self) -> Agent:
        """Return a new Agent with completed task."""
        return Agent(
            id=self.id,
            contract=self.contract,
            status=AgentStatus.IDLE,
            created_at=self.created_at,
            last_active_at=datetime.utcnow(),
            current_task_id=None,
            metadata=self.metadata,
        )

    def release(self) -> Agent:
        """Return a new Agent released from current task."""
        return Agent(
            id=self.id,
            contract=self.contract,
            status=AgentStatus.IDLE,
            created_at=self.created_at,
            last_active_at=datetime.utcnow(),
            current_task_id=None,
            metadata=self.metadata,
        )

    def terminate(self) -> Agent:
        """Return a new terminated Agent."""
        return Agent(
            id=self.id,
            contract=self.contract,
            status=AgentStatus.TERMINATED,
            created_at=self.created_at,
            last_active_at=datetime.utcnow(),
            current_task_id=None,
            metadata=self.metadata,
        )


# Pre-defined agent contracts for common agent types

OPERATOR_CONTRACT = AgentContract(
    agent_type=AgentType.OPERATOR,
    name="ACC Operator",
    description="Main user-facing agent for command execution and chat",
    capabilities=[
        AgentCapability(
            name="chat.respond",
            description="Generate conversational responses",
            risk_level=1,
        ),
        AgentCapability(
            name="command.execute",
            description="Execute shell commands",
            risk_level=4,
        ),
        AgentCapability(
            name="file.read",
            description="Read files from the filesystem",
            risk_level=2,
        ),
        AgentCapability(
            name="file.write",
            description="Write files to the filesystem",
            risk_level=4,
        ),
        AgentCapability(
            name="code.analyze",
            description="Analyze code for bugs and issues",
            risk_level=1,
        ),
    ],
    max_concurrent_tasks=1,
    timeout_seconds=300,
)

PLANNER_CONTRACT = AgentContract(
    agent_type=AgentType.PLANNER,
    name="ACC Planner",
    description="Agent specialized in planning and task decomposition",
    capabilities=[
        AgentCapability(
            name="goal.decompose",
            description="Break down goals into tasks",
            risk_level=1,
        ),
        AgentCapability(
            name="task.prioritize",
            description="Prioritize tasks based on dependencies",
            risk_level=1,
        ),
        AgentCapability(
            name="risk.assess",
            description="Assess risks in a plan",
            risk_level=1,
        ),
    ],
    max_concurrent_tasks=2,
    timeout_seconds=120,
)


__all__ = [
    "Agent",
    "AgentCapability",
    "AgentContract",
    "AgentStatus",
    "AgentType",
    "OPERATOR_CONTRACT",
    "PLANNER_CONTRACT",
]
