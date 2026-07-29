"""Global context bar state projection.

Promotes chat-local context fields into a shell-wide snapshot so the
GlobalContextBar can render the same information from every workspace.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CONTEXT_SNAPSHOT_CREATED,
    GOAL_ACTIVATED,
    GOAL_CANCELLED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    GOAL_PAUSED,
    GOAL_RESUMED,
    GOAL_SUBMITTED,
    UI_CONTEXT_CLEAR,
    UI_CONTEXT_SELECT,
    UI_OPEN_CHAT,
    UI_SELECT_ENTITY,
    WORKSPACE_ACTIVE,
)

_ACTIVE_GOAL_TOPICS = frozenset(
    {
        GOAL_SUBMITTED,
        GOAL_ACTIVATED,
        GOAL_RESUMED,
    }
)
_CLEAR_ACTIVE_GOAL_TOPICS = frozenset(
    {
        GOAL_COMPLETED,
        GOAL_FAILED,
        GOAL_CANCELLED,
        GOAL_PAUSED,
    }
)


@dataclass(frozen=True, slots=True)
class GlobalContextSnapshot:
    """Shell-wide context state shown in the global context bar."""

    workspace_id: str = ""
    workspace_title: str = ""
    entity_id: str = ""
    entity_type: str = ""
    entity_title: str = ""
    active_goal_id: str = ""
    active_goal_title: str = ""
    sources: tuple[str, ...] = ()
    token_estimate: int = 0
    revision: int = 0


def _coerce_sources(raw: Any) -> tuple[str, ...]:
    if isinstance(raw, (list, tuple)):
        return tuple(str(item) for item in raw)
    return ()


def _goal_fields(payload: dict[str, Any]) -> tuple[str, str]:
    """Extract ``(goal_id, title)`` from goal event payloads."""
    goal_payload = payload.get("goal")
    nested = goal_payload if isinstance(goal_payload, dict) else {}
    goal_id = str(
        payload.get("goal_id")
        or nested.get("id")
        or payload.get("id")
        or ""
    ).strip()
    if isinstance(goal_payload, dict):
        title = str(
            nested.get("text")
            or nested.get("title")
            or payload.get("text")
            or payload.get("title")
            or ""
        ).strip()
    else:
        title = str(
            payload.get("text")
            or payload.get("title")
            or (goal_payload if isinstance(goal_payload, str) else "")
            or ""
        ).strip()
    return goal_id, title


def resolve_active_goal(brain_state: Any) -> tuple[str, str]:
    """Return ``(goal_id, title)`` for the first active/queued/running brain goal."""
    goals = list(getattr(brain_state, "recent_goals", ()) or ())
    for goal in goals:
        status = str(getattr(goal, "status", "")).lower()
        if status in {"active", "queued", "running"}:
            return (
                str(getattr(goal, "goal_id", "") or ""),
                str(getattr(goal, "text", "") or getattr(goal, "title", "") or ""),
            )
    return ("", "")


def reduce_global_context_state(state: Any, event: Event) -> Any:
    """Update the global_context field on AppState from bus events."""
    if not hasattr(state, "global_context"):
        return state

    current: GlobalContextSnapshot = state.global_context
    topic = event.topic
    payload = event.payload or {}

    if topic == CONTEXT_SNAPSHOT_CREATED:
        sources = _coerce_sources(payload.get("sources", current.sources))
        tokens = int(payload.get("context_size_tokens", current.token_estimate))
        workspace_id = str(payload.get("workspace_id", current.workspace_id)).strip()
        new = replace(
            current,
            sources=sources,
            token_estimate=tokens,
            workspace_id=workspace_id or current.workspace_id,
            revision=current.revision + 1,
        )
        return replace(state, global_context=new)

    if topic == WORKSPACE_ACTIVE:
        ws_id = str(payload.get("workspace_id", "")).strip()
        title = str(payload.get("title", "")).strip()
        if ws_id:
            new = replace(
                current,
                workspace_id=ws_id,
                workspace_title=title,
                revision=current.revision + 1,
            )
            return replace(state, global_context=new)
        return state

    if topic in (UI_SELECT_ENTITY, UI_CONTEXT_SELECT):
        entity_id = str(payload.get("entity_id", "")).strip()
        if entity_id:
            new = replace(
                current,
                entity_id=entity_id,
                entity_type=str(payload.get("entity_type", "")).strip(),
                entity_title=str(payload.get("title", "")).strip(),
                revision=current.revision + 1,
            )
            return replace(state, global_context=new)
        return state

    if topic == UI_OPEN_CHAT:
        entity_id = str(payload.get("entity_id", "")).strip()
        if not entity_id:
            new = replace(
                current,
                entity_id="",
                entity_type="",
                entity_title="",
                revision=current.revision + 1,
            )
            return replace(state, global_context=new)
        new = replace(
            current,
            entity_id=entity_id,
            entity_type=str(payload.get("entity_type", "")).strip(),
            entity_title=str(payload.get("title", "")).strip(),
            revision=current.revision + 1,
        )
        return replace(state, global_context=new)

    if topic == UI_CONTEXT_CLEAR:
        new = replace(
            current,
            entity_id="",
            entity_type="",
            entity_title="",
            sources=(),
            token_estimate=0,
            revision=current.revision + 1,
        )
        return replace(state, global_context=new)

    if topic in _ACTIVE_GOAL_TOPICS:
        goal_id, title = _goal_fields(payload)
        goal_id = goal_id or current.active_goal_id
        title = title or current.active_goal_title
        if goal_id or title:
            new = replace(
                current,
                active_goal_id=goal_id,
                active_goal_title=title,
                revision=current.revision + 1,
            )
            return replace(state, global_context=new)
        return state

    if topic in _CLEAR_ACTIVE_GOAL_TOPICS:
        goal_id, _ = _goal_fields(payload)
        if not goal_id or goal_id == current.active_goal_id:
            new = replace(
                current,
                active_goal_id="",
                active_goal_title="",
                revision=current.revision + 1,
            )
            return replace(state, global_context=new)
        return state

    return state
