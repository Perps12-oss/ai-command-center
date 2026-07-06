"""Chat AppState reducers (Program 3 W4 domain split)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_CHUNK,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CHAT_STARTED,
    COMMAND_ROUTED,
    CONTEXT_SNAPSHOT_CREATED,
    UI_CHAT_NEW_SESSION,
    UI_OPEN_CHAT,
)


def _coerce_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def _is_pending_chat_user_text(text: str) -> bool:
    """Mirror shell logic: only plain chat prompts become pending user bubbles."""
    stripped = text.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if lower.startswith(
        ("note:", "new note:", "remember:", "memory:", "agent:", ">", "go ")
    ):
        return False
    if lower in (
        "settings",
        "chat",
        "notes",
        "plugins",
        "home",
        "workspace",
        "system",
        "memory",
    ):
        return False
    return True


def _reduce_command_routed(state: Any, event: Event) -> Any:
    if event.topic != COMMAND_ROUTED:
        return state
    text = str(event.payload.get("text", ""))
    pending = text if _is_pending_chat_user_text(text) else ""
    args = event.payload.get("args") or {}
    workspace_id = str(event.payload.get("workspace_id") or args.get("workspace_id", "")).strip()
    updates: dict[str, object] = {
        "last_command": text,
        "last_command_intent": str(event.payload.get("intent", "")),
        "chat_pending_user_text": pending,
        "last_event_topic": event.topic,
        "last_event_source": event.source,
    }
    if workspace_id:
        updates["last_workspace_context_workspace_id"] = workspace_id
    return replace(state, **updates)


def _reduce_chat_started(state: Any, event: Event) -> Any:
    if event.topic != CHAT_STARTED:
        return state
    request_id = str(event.payload.get("request_id", ""))
    if request_id and state.active_chat_request_id == request_id and state.chat_streaming:
        return state
    return replace(
        state,
        active_chat_request_id=request_id,
        last_chat_request_id=request_id,
        chat_status="streaming",
        chat_streaming=True,
        chat_stream_buffer="",
        chat_stream_revision=state.chat_stream_revision + 1,
        chat_started_user_text=state.chat_pending_user_text,
        chat_pending_user_text="",
        last_chat_error="",
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_chat_chunk(state: Any, event: Event) -> Any:
    if event.topic != CHAT_CHUNK:
        return state
    request_id = str(event.payload.get("request_id", ""))
    if request_id and request_id != state.active_chat_request_id:
        return state
    text = str(event.payload.get("text", ""))
    if not text:
        return state
    return replace(
        state,
        chat_stream_buffer=state.chat_stream_buffer + text,
        chat_stream_revision=state.chat_stream_revision + 1,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_chat_complete(state: Any, event: Event) -> Any:
    if event.topic != CHAT_COMPLETE:
        return state
    request_id = str(event.payload.get("request_id", ""))
    if request_id:
        if not state.active_chat_request_id:
            return state
        if request_id != state.active_chat_request_id:
            return state
    return replace(
        state,
        active_chat_request_id="",
        chat_status="complete",
        chat_streaming=False,
        chat_stream_buffer="",
        chat_stream_revision=state.chat_stream_revision + 1,
        chat_started_user_text="",
        last_assistant_message=str(event.payload.get("text", "")),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_chat_cancelled(state: Any, event: Event) -> Any:
    if event.topic != CHAT_CANCELLED:
        return state
    request_id = str(event.payload.get("request_id", ""))
    if request_id:
        if not state.active_chat_request_id:
            return state
        if request_id != state.active_chat_request_id:
            return state
    return replace(
        state,
        active_chat_request_id="",
        chat_status="cancelled",
        chat_streaming=False,
        chat_stream_buffer="",
        chat_stream_revision=state.chat_stream_revision + 1,
        chat_started_user_text="",
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_chat_error(state: Any, event: Event) -> Any:
    if event.topic != CHAT_ERROR:
        return state
    request_id = str(event.payload.get("request_id", ""))
    if request_id:
        if not state.active_chat_request_id:
            return state
        if request_id != state.active_chat_request_id:
            return state
    return replace(
        state,
        active_chat_request_id="",
        chat_status="error",
        chat_streaming=False,
        chat_stream_buffer="",
        chat_stream_revision=state.chat_stream_revision + 1,
        chat_started_user_text="",
        last_chat_error=str(event.payload.get("message", "Unknown error")),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_chat_history_loaded(state: Any, event: Event) -> Any:
    if event.topic != CHAT_HISTORY_LOADED:
        return state
    from ai_command_center.core.app_state import ChatHistoryMessage

    raw_messages = event.payload.get("messages")
    items: list[ChatHistoryMessage] = []
    if isinstance(raw_messages, list):
        for item in raw_messages:
            if not isinstance(item, dict):
                continue
            items.append(
                ChatHistoryMessage(
                    role=str(item.get("role", "")),
                    content=str(item.get("content", "")),
                )
            )
    return replace(
        state,
        chat_history_count=len(items),
        chat_history_messages=tuple(items),
        chat_history_revision=state.chat_history_revision + 1,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_context_snapshot(state: Any, event: Event) -> Any:
    if event.topic != CONTEXT_SNAPSHOT_CREATED:
        return state
    raw_sources = event.payload.get("sources", [])
    sources = tuple(str(item) for item in raw_sources) if isinstance(raw_sources, (list, tuple)) else ()
    tokens = _coerce_int(event.payload.get("context_size_tokens", 0), 0)
    raw_workspace_snippets = event.payload.get("workspace_context_snippets", [])
    snippet_count = (
        len(raw_workspace_snippets)
        if isinstance(raw_workspace_snippets, (list, tuple))
        else 0
    )
    workspace_id = str(event.payload.get("workspace_id", "")).strip()
    return replace(
        state,
        chat_context_sources=sources,
        chat_token_estimate=tokens,
        workspace_context_snippet_count=snippet_count,
        last_workspace_context_workspace_id=workspace_id,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _entity_session_key(entity_type: str, entity_id: str) -> str:
    return f"entity:{entity_type}:{entity_id}"


def _clear_chat_entity_fields(state: Any, event: Event) -> Any:
    return replace(
        state,
        chat_workspace_entity_id="",
        chat_workspace_entity_type="",
        chat_workspace_entity_title="",
        chat_workspace_entity_description="",
        chat_workspace_entity_url="",
        chat_workspace_entity_path="",
        chat_active_session_key="default",
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_chat_workspace_entity(state: Any, event: Event) -> Any:
    """Project workspace-attached chat entity from ui.workspace_os.open_chat."""
    if event.topic != UI_OPEN_CHAT:
        return state
    entity_id = str(event.payload.get("entity_id", "")).strip()
    if not entity_id:
        return _clear_chat_entity_fields(state, event)
    entity_type = str(event.payload.get("entity_type", ""))
    return replace(
        state,
        chat_workspace_entity_id=entity_id,
        chat_workspace_entity_type=entity_type,
        chat_workspace_entity_title=str(event.payload.get("title", "")),
        chat_workspace_entity_description=str(event.payload.get("description", "")),
        chat_workspace_entity_url=str(event.payload.get("url", "")),
        chat_workspace_entity_path=str(event.payload.get("path", "")),
        chat_active_session_key=_entity_session_key(entity_type, entity_id),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_ui_chat_new_session(state: Any, event: Event) -> Any:
    """Clear sticky workspace entity context when user starts a fresh chat."""
    if event.topic != UI_CHAT_NEW_SESSION:
        return state
    return _clear_chat_entity_fields(state, event)


CHAT_REDUCERS = (
    _reduce_command_routed,
    _reduce_chat_started,
    _reduce_chat_chunk,
    _reduce_chat_complete,
    _reduce_chat_cancelled,
    _reduce_chat_error,
    _reduce_chat_history_loaded,
    _reduce_context_snapshot,
    _reduce_chat_workspace_entity,
    _reduce_ui_chat_new_session,
)
