"""Workflow AppState reducers (Program 4 W4 / slice 4)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNS_LOADED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)

_MAX_WORKFLOW_RUNS = 20


@dataclass(frozen=True, slots=True)
class WorkflowRunItem:
    """Projection of a workflow run for UI rendering."""

    run_id: str = ""
    workflow_id: str = ""
    state: str = "pending"
    current_step_id: str = ""
    current_step_index: int = 0
    total_steps: int = 0
    error: str = ""


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _find_workflow_run(
    runs: tuple[WorkflowRunItem, ...], run_id: str
) -> WorkflowRunItem | None:
    for run in runs:
        if run.run_id == run_id:
            return run
    return None


def _upsert_workflow_run(
    runs: tuple[WorkflowRunItem, ...], item: WorkflowRunItem
) -> tuple[WorkflowRunItem, ...]:
    filtered = tuple(r for r in runs if r.run_id != item.run_id)
    updated = (item,) + filtered
    if len(updated) > _MAX_WORKFLOW_RUNS:
        updated = updated[:_MAX_WORKFLOW_RUNS]
    return updated


def _reduce_workflow_run(state: Any, event: Event) -> Any:
    """Project workflow lifecycle events into workflow_runs feed."""
    if event.topic not in {
        WORKFLOW_STARTED,
        WORKFLOW_STEP_STARTED,
        WORKFLOW_STEP_COMPLETED,
        WORKFLOW_COMPLETED,
        WORKFLOW_FAILED,
    }:
        return state

    payload = event.payload
    run_id = str(payload.get("run_id", ""))
    if not run_id:
        return state

    existing = _find_workflow_run(state.workflow_runs, run_id)
    workflow_id = str(
        payload.get("workflow_id") or (existing.workflow_id if existing else "")
    )
    total_steps = _coerce_int(
        payload.get("total_steps"),
        existing.total_steps if existing else 0,
    )
    step_id = str(payload.get("step_id") or (existing.current_step_id if existing else ""))
    step_index = _coerce_int(
        payload.get("index"),
        existing.current_step_index if existing else 0,
    )
    if event.topic == WORKFLOW_COMPLETED:
        error = str(payload.get("error", ""))
    elif event.topic == WORKFLOW_FAILED:
        error = str(payload.get("error") or (existing.error if existing else ""))
    else:
        error = str(payload.get("error") or (existing.error if existing else ""))

    if event.topic == WORKFLOW_STARTED:
        item = WorkflowRunItem(
            run_id=run_id,
            workflow_id=workflow_id,
            state="running",
            total_steps=total_steps,
        )
        return replace(
            state,
            workflow_runs=_upsert_workflow_run(state.workflow_runs, item),
            active_workflow_run_id=run_id,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if existing is None:
        existing = WorkflowRunItem(run_id=run_id, workflow_id=workflow_id, state="running")

    if event.topic == WORKFLOW_STEP_STARTED:
        run_state = "running"
    elif event.topic == WORKFLOW_STEP_COMPLETED:
        run_state = "running"
        step_index = step_index + 1
    elif event.topic == WORKFLOW_COMPLETED:
        run_state = "completed"
    elif event.topic == WORKFLOW_FAILED:
        run_state = "failed"
    else:
        run_state = existing.state

    item = WorkflowRunItem(
        run_id=run_id,
        workflow_id=workflow_id or existing.workflow_id,
        state=run_state,
        current_step_id=step_id or existing.current_step_id,
        current_step_index=step_index,
        total_steps=total_steps or existing.total_steps,
        error=error,
    )
    active_id = state.active_workflow_run_id
    if event.topic in {WORKFLOW_COMPLETED, WORKFLOW_FAILED} and active_id == run_id:
        active_id = ""

    return replace(
        state,
        workflow_runs=_upsert_workflow_run(state.workflow_runs, item),
        active_workflow_run_id=active_id,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_workflow_runs_loaded(state: Any, event: Event) -> Any:
    """Hydrate workflow_runs feed from persisted metadata on startup."""
    if event.topic != WORKFLOW_RUNS_LOADED:
        return state
    raw_runs = event.payload.get("runs")
    if not isinstance(raw_runs, list) or not raw_runs:
        return state

    runs = state.workflow_runs
    for raw in raw_runs:
        if not isinstance(raw, dict):
            continue
        run_id = str(raw.get("run_id", ""))
        if not run_id or _find_workflow_run(runs, run_id) is not None:
            continue
        item = WorkflowRunItem(
            run_id=run_id,
            workflow_id=str(raw.get("workflow_id", "")),
            state=str(raw.get("state", "completed")),
            current_step_index=_coerce_int(raw.get("current_step_index"), 0),
            total_steps=_coerce_int(raw.get("total_steps"), 0),
            error=str(raw.get("error", "")),
        )
        runs = _upsert_workflow_run(runs, item)

    return replace(
        state,
        workflow_runs=runs,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


WORKFLOW_REDUCERS: tuple[Any, ...] = (
    _reduce_workflow_run,
    _reduce_workflow_runs_loaded,
)
