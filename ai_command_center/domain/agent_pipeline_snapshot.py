"""Immutable AppState snapshot for the Agent Pipeline.

Consolidates existing AppState agent/pipeline fields into one typed snapshot:
  agent_runs              (tuple[AgentRunItem])
  active_agent_run_id     (str)
  active_agent_run_ids    (tuple[str,...])
  active_agent_pipeline_id (str)
  agent_pipeline_stage    (str)
  agent_pipeline_planned_tools (tuple[str,...])

Consumers should prefer AppState.agent_pipeline over the raw fields.
The raw fields are retained for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentRunSnapshot:
    """Immutable snapshot of a single agent run."""

    agent_id: str = ""
    request_id: str = ""
    state: str = "spawning"
    task: str = ""
    error: str = ""
    steps: int = 0
    workspace_id: str = ""
    workspace_entity_id: str = ""
    spawn_role: str = ""

    @property
    def is_active(self) -> bool:
        return self.state in {"spawning", "running", "waiting"}

    @property
    def is_terminal(self) -> bool:
        return self.state in {"terminated", "failed"}


@dataclass(frozen=True, slots=True)
class AgentPipelineSnapshot:
    """Immutable AppState projection of agent runs and pipeline orchestration."""

    runs: tuple[AgentRunSnapshot, ...] = ()
    active_run_id: str = ""
    active_run_ids: tuple[str, ...] = ()
    pipeline_id: str = ""
    pipeline_stage: str = ""
    planned_tools: tuple[str, ...] = ()
    total_spawned: int = 0

    @property
    def active_runs(self) -> tuple[AgentRunSnapshot, ...]:
        return tuple(r for r in self.runs if r.is_active)

    @property
    def active_run(self) -> AgentRunSnapshot | None:
        if not self.active_run_id:
            return None
        for r in self.runs:
            if r.agent_id == self.active_run_id:
                return r
        return None

    @property
    def pipeline_active(self) -> bool:
        return bool(self.pipeline_id) and self.pipeline_stage not in {"", "complete"}

    def run_by_id(self, agent_id: str) -> AgentRunSnapshot | None:
        for r in self.runs:
            if r.agent_id == agent_id:
                return r
        return None
