"""Tool AppState reducers (Program 4 W4 partial)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import TOOL_COMPLETED, TOOL_FAILED, TOOL_STARTED

_MAX_TOOL_RUNS = 20


@dataclass(frozen=True, slots=True)
class ToolRunItem:
    """Projection of a tool execution for AppState feeds."""

    invoke_id: str = ""
    tool: str = ""
    status: str = "running"
    error: str = ""
    message: str = ""


def _upsert_tool_run(
    runs: tuple[ToolRunItem, ...], item: ToolRunItem
) -> tuple[ToolRunItem, ...]:
    if item.invoke_id:
        filtered = tuple(r for r in runs if r.invoke_id != item.invoke_id)
    else:
        filtered = runs
    updated = (item,) + filtered
    if len(updated) > _MAX_TOOL_RUNS:
        updated = updated[:_MAX_TOOL_RUNS]
    return updated


def _find_tool_run(runs: tuple[ToolRunItem, ...], invoke_id: str) -> ToolRunItem | None:
    if not invoke_id:
        return None
    for run in runs:
        if run.invoke_id == invoke_id:
            return run
    return None


def _reduce_tool_started(state: Any, event: Event) -> Any:
    if event.topic != TOOL_STARTED:
        return state
    payload = event.payload
    invoke_id = str(payload.get("invoke_id", ""))
    tool = str(payload.get("tool", ""))
    if not tool:
        return state
    item = ToolRunItem(invoke_id=invoke_id, tool=tool, status="running")
    return replace(
        state,
        recent_tool_runs=_upsert_tool_run(state.recent_tool_runs, item),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_tool_completed(state: Any, event: Event) -> Any:
    if event.topic != TOOL_COMPLETED:
        return state
    payload = event.payload
    invoke_id = str(payload.get("invoke_id", ""))
    tool = str(payload.get("tool", ""))
    existing = _find_tool_run(state.recent_tool_runs, invoke_id)
    item = ToolRunItem(
        invoke_id=invoke_id or (existing.invoke_id if existing else ""),
        tool=tool or (existing.tool if existing else ""),
        status="completed",
    )
    if not item.tool:
        return state
    return replace(
        state,
        recent_tool_runs=_upsert_tool_run(state.recent_tool_runs, item),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_tool_failed(state: Any, event: Event) -> Any:
    if event.topic != TOOL_FAILED:
        return state
    payload = event.payload
    invoke_id = str(payload.get("invoke_id", ""))
    tool = str(payload.get("tool", ""))
    error = str(payload.get("error", ""))
    message = str(payload.get("message", ""))
    existing = _find_tool_run(state.recent_tool_runs, invoke_id)
    item = ToolRunItem(
        invoke_id=invoke_id or (existing.invoke_id if existing else ""),
        tool=tool or (existing.tool if existing else ""),
        status="failed",
        error=error,
        message=message,
    )
    if not item.tool:
        return state
    return replace(
        state,
        recent_tool_runs=_upsert_tool_run(state.recent_tool_runs, item),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


TOOL_REDUCERS: tuple[Any, ...] = (
    _reduce_tool_started,
    _reduce_tool_completed,
    _reduce_tool_failed,
)
