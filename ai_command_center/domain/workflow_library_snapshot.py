"""Immutable AppState snapshot for the Workflow Library.

Consolidates existing AppState workflow fields into one typed snapshot:
  workflow_runs          (tuple[WorkflowRunItem])
  active_workflow_run_id (str)

Adds step-level detail not available in the lightweight WorkflowRunItem.
Consumers should prefer AppState.workflow_library over the raw fields.
The raw fields are retained for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkflowStepSnapshot:
    """Immutable snapshot of a single workflow step."""

    step_id: str = ""
    run_id: str = ""
    index: int = 0
    status: str = "pending"   # pending | running | completed | failed


@dataclass(frozen=True, slots=True)
class WorkflowRunSnapshot:
    """Immutable snapshot of a single workflow run with step detail."""

    run_id: str = ""
    workflow_id: str = ""
    state: str = "pending"    # running | completed | failed | pending
    current_step_id: str = ""
    current_step_index: int = 0
    total_steps: int = 0
    error: str = ""
    steps: tuple[WorkflowStepSnapshot, ...] = ()

    @property
    def is_active(self) -> bool:
        return self.state == "running"

    @property
    def is_terminal(self) -> bool:
        return self.state in {"completed", "failed"}

    @property
    def progress(self) -> float:
        if not self.total_steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == "completed")
        return completed / self.total_steps

    @property
    def current_step(self) -> WorkflowStepSnapshot | None:
        if not self.current_step_id:
            return None
        for s in self.steps:
            if s.step_id == self.current_step_id:
                return s
        return None


_MAX_WORKFLOW_HISTORY = 50


@dataclass(frozen=True, slots=True)
class WorkflowLibrarySnapshot:
    """Immutable AppState projection of workflow run history."""

    runs: tuple[WorkflowRunSnapshot, ...] = ()
    active_run_id: str = ""
    total_started: int = 0
    total_completed: int = 0
    total_failed: int = 0

    @property
    def active_run(self) -> WorkflowRunSnapshot | None:
        if not self.active_run_id:
            return None
        for r in self.runs:
            if r.run_id == self.active_run_id:
                return r
        return None

    def run_by_id(self, run_id: str) -> WorkflowRunSnapshot | None:
        for r in self.runs:
            if r.run_id == run_id:
                return r
        return None
