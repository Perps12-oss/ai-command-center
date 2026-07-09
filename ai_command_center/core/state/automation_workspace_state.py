"""Automation workspace AppState reducers (ACC UI Refurbishment PR 14–15)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    UI_AUTOMATION_RUN,
    UI_AUTOMATION_SELECT,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNS_LOADED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)
from ai_command_center.core.projectors.automation_workspace_projector import (
    AutomationWorkspaceProjector,
)
from ai_command_center.domain.automation_workspace import AutomationWorkspaceState

_WORKFLOW_TOPICS = {
    WORKFLOW_STARTED,
    WORKFLOW_STEP_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNS_LOADED,
}


def _workflow_runs_from_state(state: Any) -> tuple[Any, ...]:
    return tuple(getattr(state, "workflow_runs", ()) or ())


def _rebuild_state(state: Any, *, selected_failure_run_id: str | None = None) -> Any:
    current: AutomationWorkspaceState = state.automation_workspace
    selected = (
        current.selected_failure_run_id
        if selected_failure_run_id is None
        else selected_failure_run_id
    )
    projected = AutomationWorkspaceProjector.project_state(
        _workflow_runs_from_state(state),
        selected_failure_run_id=selected,
        revision=current.revision + 1,
    )
    return replace(state, automation_workspace=projected)


def reduce_automation_workspace_state(state: Any, event: Event) -> Any:
    """Pure reducer for automation workspace projections."""
    if event.topic in _WORKFLOW_TOPICS:
        return _rebuild_state(state)

    if event.topic == UI_AUTOMATION_SELECT:
        run_id = str(event.payload.get("run_id") or "")
        if not run_id or run_id == state.automation_workspace.selected_failure_run_id:
            return state
        return _rebuild_state(state, selected_failure_run_id=run_id)

    if event.topic == UI_AUTOMATION_RUN:
        return _rebuild_state(state)

    return state


__all__ = ["reduce_automation_workspace_state"]
