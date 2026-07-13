"""Immutable AppState snapshot for the Execution Library.

Consolidates three existing AppState projections into one typed snapshot:
  execution_active_plan   (raw dict, from EXECUTION_RUN_* topics)
  execution_current_step  (raw dict, from EXECUTION_STEP_* topics)
  execution_runs          (tuple[ExecutionRunItem], lightweight feed)

Consumers should prefer AppState.execution_library over the raw fields.
The raw fields are retained for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionStepSnapshot:
    """Immutable snapshot of a single execution step."""

    step_id: str = ""
    run_id: str = ""
    index: int = 0
    capability: str = ""
    risk: str = ""
    status: str = "pending"
    error: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionPlanSnapshot:
    """Immutable snapshot of an active execution plan."""

    run_id: str = ""
    request_id: str = ""
    goal: str = ""
    total_steps: int = 0
    status: str = "idle"
    error: str = ""
    current_step_id: str = ""
    steps: tuple[ExecutionStepSnapshot, ...] = ()

    @property
    def is_active(self) -> bool:
        return self.status in {"running", "awaiting_approval"}

    @property
    def current_step(self) -> ExecutionStepSnapshot | None:
        if not self.current_step_id:
            return None
        for s in self.steps:
            if s.step_id == self.current_step_id:
                return s
        return None

    @property
    def completed_steps(self) -> tuple[ExecutionStepSnapshot, ...]:
        return tuple(s for s in self.steps if s.status == "completed")

    @property
    def progress(self) -> float:
        if not self.total_steps:
            return 0.0
        return len(self.completed_steps) / self.total_steps


@dataclass(frozen=True, slots=True)
class ExecutionRunEntry:
    """Lightweight run history entry."""

    run_id: str = ""
    request_id: str = ""
    source: str = ""
    created_at: float = 0.0
    summary: str = ""
    status: str = "complete"


_MAX_RUN_HISTORY = 50


@dataclass(frozen=True, slots=True)
class ExecutionLibrarySnapshot:
    """Immutable AppState projection of the execution system."""

    active_plan: ExecutionPlanSnapshot = ExecutionPlanSnapshot()
    run_history: tuple[ExecutionRunEntry, ...] = ()
    total_runs: int = 0

    @property
    def last_run(self) -> ExecutionRunEntry | None:
        return self.run_history[0] if self.run_history else None
