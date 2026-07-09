"""Automation workspace projector tests."""

from __future__ import annotations

from dataclasses import dataclass

from ai_command_center.core.projectors.automation_workspace_projector import (
    AutomationWorkspaceProjector,
)


@dataclass(frozen=True, slots=True)
class _Run:
    run_id: str
    workflow_id: str
    state: str
    current_step_id: str = ""
    current_step_index: int = 0
    total_steps: int = 0
    error: str = ""


def test_project_state_includes_static_catalog_and_templates() -> None:
    state = AutomationWorkspaceProjector.project_state(())
    assert len(state.catalog) >= 3
    assert len(state.templates) >= 3
    assert len(state.schedules) >= 2


def test_project_runs_splits_active_and_failed() -> None:
    runs = (
        _Run("r1", "demo", "running", current_step_index=1, total_steps=3),
        _Run("r2", "demo", "failed", current_step_index=2, total_steps=3, error="boom"),
        _Run("r3", "demo", "completed", total_steps=2),
    )
    active, failures = AutomationWorkspaceProjector.project_runs(runs)
    assert len(active) == 1
    assert len(failures) == 1
    assert failures[0].error == "boom"


def test_steps_for_workflow_returns_demo_by_default() -> None:
    steps = AutomationWorkspaceProjector.steps_for_workflow("unknown")
    assert len(steps) == 3
