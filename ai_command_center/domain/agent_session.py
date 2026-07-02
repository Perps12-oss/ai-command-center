"""Agent session domain model (Agent Framework A0)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    SPAWNING = "spawning"
    RUNNING = "running"
    WAITING = "waiting"
    TERMINATED = "terminated"


@dataclass(frozen=True, slots=True)
class AgentSession:
    agent_id: str
    parent_workspace_id: str | None
    state: AgentState
    capabilities: tuple[str, ...] = ()
    request_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
