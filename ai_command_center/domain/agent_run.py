"""Agent run domain model (Agent Framework A0 / R7 AppState projection)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentRunState(str, Enum):
    SPAWNING = "spawning"
    RUNNING = "running"
    WAITING = "waiting"
    TERMINATED = "terminated"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AgentRunSnapshot:
    """Immutable snapshot of a single agent run for AppState projection."""

    agent_id: str
    request_id: str
    state: AgentRunState
    task: str = ""
    error: str = ""
    steps: int = 0
    workspace_id: str = ""
    workspace_entity_id: str = ""
    spawn_role: str = ""
