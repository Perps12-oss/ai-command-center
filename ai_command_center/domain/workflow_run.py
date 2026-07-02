"""Workflow run domain model (Workflow Engine W0 / R7 AppState projection)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkflowRunState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class WorkflowRunSnapshot:
    """Immutable snapshot of a single workflow run for AppState projection."""

    run_id: str
    workflow_id: str
    state: WorkflowRunState
    current_step_id: str = ""
    current_step_index: int = 0
    total_steps: int = 0
    error: str = ""
