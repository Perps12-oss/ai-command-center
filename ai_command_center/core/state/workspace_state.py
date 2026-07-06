"""Workspace AppState reducers (Program 3 W4 domain split)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ai_command_center.core.event_bus import (
    EVENT_ACTION_REGISTERED,
    EVENT_RELATIONSHIP_CREATED,
    EVENT_TIMELINE_EVENT,
    Event,
)
from ai_command_center.core.events.topics import (
    ENTITY_CREATED,
    ENTITY_DELETED,
    ENTITY_UPDATED,
    NOTES_INDEXED,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)


def _freeze_metadata(raw: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, dict):
        return ()
    return tuple((str(k), str(v)) for k, v in raw.items() if v is not None)


def _reduce_workspace_os_event(state: Any, event: Event) -> Any:
    """Update Workspace OS counters, recent events, and entity list."""
    from ai_command_center.core.app_state import WorkspaceOsEntity

    current = state.workspace_os
    if event.topic == ENTITY_CREATED:
        raw_meta = event.payload.get("metadata", {})
        meta = _freeze_metadata(raw_meta)
        entity = WorkspaceOsEntity(
            entity_id=str(event.payload.get("entity_id", "")),
            entity_type=str(event.payload.get("entity_type", "")),
            title=str(event.payload.get("title", "")),
            metadata=meta,
        )
        snapshot = replace(
            current,
            entity_count=current.entity_count + 1,
            entities=current.entities + (entity,),
        )
    elif event.topic == ENTITY_UPDATED:
        updated_id = str(event.payload.get("entity_id", ""))
        meta = _freeze_metadata(event.payload.get("metadata", {}))
        updated = tuple(
            WorkspaceOsEntity(
                entity_id=updated_id,
                entity_type=str(event.payload.get("entity_type", e.entity_type)),
                title=str(event.payload.get("title", e.title)),
                metadata=meta if meta else e.metadata,
            )
            if e.entity_id == updated_id
            else e
            for e in current.entities
        )
        snapshot = replace(current, entities=updated)
    elif event.topic == ENTITY_DELETED:
        deleted_id = str(event.payload.get("entity_id", ""))
        remaining = tuple(e for e in current.entities if e.entity_id != deleted_id)
        snapshot = replace(
            current,
            entity_count=max(0, current.entity_count - 1),
            entities=remaining,
        )
    elif event.topic == EVENT_RELATIONSHIP_CREATED:
        snapshot = replace(current, relationship_count=current.relationship_count + 1)
    elif event.topic == EVENT_ACTION_REGISTERED:
        snapshot = replace(current, action_count=current.action_count + 1)
    elif event.topic == EVENT_TIMELINE_EVENT:
        recent = current.recent_events + (str(event.payload.get("event_type", event.topic)),)
        if len(recent) > 20:
            recent = recent[-20:]
        snapshot = replace(
            current,
            event_count=current.event_count + 1,
            recent_events=recent,
        )
    else:
        return state
    return replace(
        state,
        workspace_os=snapshot,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_notes_indexed(state: Any, event: Event) -> Any:
    """Project indexed vault notes as entity_type=note on workspace canvas (W2)."""
    from ai_command_center.core.app_state import WorkspaceOsEntity

    if event.topic != NOTES_INDEXED:
        return state
    raw = event.payload.get("notes") or []
    note_entities: list[WorkspaceOsEntity] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", item.get("entity_id", "")))
        note_entities.append(
            WorkspaceOsEntity(
                entity_id=str(item.get("entity_id", path)),
                entity_type="note",
                title=str(item.get("title", path)),
                metadata=_freeze_metadata({"path": path}),
            )
        )
    current = state.workspace_os
    non_notes = tuple(e for e in current.entities if e.entity_type != "note")
    merged = non_notes + tuple(note_entities)
    old_note_count = sum(1 for e in current.entities if e.entity_type == "note")
    entity_count = current.entity_count - old_note_count + len(note_entities)
    return replace(
        state,
        workspace_os=replace(current, entities=merged, entity_count=entity_count),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_workspace_active(state: Any, event: Event) -> Any:
    """Project active workspace scope from workspace.active / workspace.deactivated."""
    if event.topic == WORKSPACE_ACTIVE:
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        title = str(event.payload.get("title", "")).strip()
        return replace(
            state,
            active_workspace_id=workspace_id,
            active_workspace_title=title,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    if event.topic == WORKSPACE_DEACTIVATED:
        cleared_id = str(event.payload.get("workspace_id", "")).strip()
        if cleared_id and cleared_id != state.active_workspace_id:
            return state
        return replace(
            state,
            active_workspace_id="",
            active_workspace_title="",
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    return state


WORKSPACE_REDUCERS = (
    _reduce_workspace_os_event,
    _reduce_notes_indexed,
    _reduce_workspace_active,
)
