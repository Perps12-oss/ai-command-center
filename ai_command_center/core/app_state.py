"""Central application state — updated only via event reducers."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from ai_command_center.core.event_bus import (
    EVENT_ACTION_REGISTERED,
    EVENT_ENTITY_CREATED,
    EVENT_ENTITY_DELETED,
    EVENT_ENTITY_RELATIONSHIPS_CHANGED,
    EVENT_ENTITY_UPDATED,
    EVENT_RELATIONSHIP_CREATED,
    EVENT_TIMELINE_EVENT,
    Event,
    EventBus,
)
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_TASK_COMPLETE,
    AGENT_TASK_REQUEST,
    AGENT_TERMINATED,
    APP_ERROR,
    APP_PHASE,
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
    CHAT_CANCELLED,
    CHAT_CHUNK,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CHAT_STARTED,
    COMMAND_ROUTED,
    CONTEXT_SNAPSHOT_CREATED,
    MEMORY_CLEARED,
    MEMORY_SELECTED,
    MEMORY_STORED,
    NOTE_CREATED,
    NOTE_INDEX_COMPLETE,
    NOTE_SEARCH_RESULTS,
    NOTE_SELECTED,
    PLUGIN_CATALOG,
    PLUGIN_STATE_CHANGED,
    SERVICE_STATE_CHANGED,
    SETTINGS_CHANGED,
    SETTINGS_SNAPSHOT,
    SYSTEM_SNAPSHOT,
    UI_OPEN_CHAT,
    UI_CHAT_NEW_SESSION,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)
from ai_command_center.domain.settings_snapshot import SettingsSnapshot
from ai_command_center.domain.system_snapshot import SystemSnapshot

logger = logging.getLogger(__name__)

APP_STATE_TOPICS: tuple[str, ...] = (
    SERVICE_STATE_CHANGED,
    SETTINGS_CHANGED,
    SETTINGS_SNAPSHOT,
    COMMAND_ROUTED,
    CHAT_STARTED,
    CHAT_CHUNK,
    CHAT_COMPLETE,
    CHAT_CANCELLED,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CONTEXT_SNAPSHOT_CREATED,
    APP_ERROR,
    APP_PHASE,
    SYSTEM_SNAPSHOT,
    # Notes / Memory / Plugins (Track 3.2)
    NOTE_SEARCH_RESULTS,
    NOTE_SELECTED,
    NOTE_CREATED,
    NOTE_INDEX_COMPLETE,
    MEMORY_STORED,
    MEMORY_SELECTED,
    MEMORY_CLEARED,
    PLUGIN_CATALOG,
    PLUGIN_STATE_CHANGED,
    # Workspace OS (Track B - Phase 2 + 3.2)
    EVENT_ENTITY_CREATED,
    EVENT_RELATIONSHIP_CREATED,
    EVENT_ACTION_REGISTERED,
    EVENT_TIMELINE_EVENT,
    EVENT_ENTITY_UPDATED,
    EVENT_ENTITY_DELETED,
    EVENT_ENTITY_RELATIONSHIPS_CHANGED,
    UI_OPEN_CHAT,
    UI_CHAT_NEW_SESSION,
    # Agent / workflow runs (Track R7)
    AGENT_SPAWNED,
    AGENT_TASK_REQUEST,
    AGENT_TASK_COMPLETE,
    AGENT_TERMINATED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
)


@dataclass(frozen=True, slots=True)
class ServiceSnapshot:
    name: str
    state: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceOsEntity:
    """Lightweight Workspace OS entity projection."""

    entity_id: str = ""
    entity_type: str = ""
    title: str = ""
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class WorkspaceOsSnapshot:
    """Workspace OS projection for the inspector UI."""

    entity_count: int = 0
    relationship_count: int = 0
    action_count: int = 0
    event_count: int = 0
    recent_events: tuple[str, ...] = ()
    entities: tuple[WorkspaceOsEntity, ...] = ()


@dataclass(frozen=True, slots=True)
class NoteItem:
    """Projection of a note search result."""

    path: str = ""
    title: str = ""
    snippet: str = ""


@dataclass(frozen=True, slots=True)
class MemoryItem:
    """Projection of a stored memory node."""

    node_id: str = ""
    label: str = ""


@dataclass(frozen=True, slots=True)
class ChatHistoryMessage:
    """Projection of a persisted chat message."""

    role: str = ""
    content: str = ""


@dataclass(frozen=True, slots=True)
class PluginItem:
    """Projection of a plugin catalog entry."""

    plugin_id: str = ""
    name: str = ""
    description: str = ""
    kind: str = "extension"
    enabled: bool = True
    error: str = ""
    pending_restart: bool = False


@dataclass(frozen=True, slots=True)
class AgentRunItem:
    """Projection of an agent run for UI rendering."""

    agent_id: str = ""
    request_id: str = ""
    state: str = "spawning"
    task: str = ""
    error: str = ""
    steps: int = 0
    workspace_id: str = ""


@dataclass(frozen=True, slots=True)
class PermissionCheckItem:
    """Pending interactive permission check surfaced to the UI."""

    check_id: str = ""
    permissions: tuple[str, ...] = ()
    actor_type: str = "agent"
    actor_id: str = ""
    summary: str = ""
    interactive: bool = False


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


_MAX_RUN_FEED = 20
@dataclass(frozen=True, slots=True)
class AppState:
    """Immutable snapshot of application state."""

    phase: str = "idle"
    services: tuple[ServiceSnapshot, ...] = ()
    settings: SettingsSnapshot = field(default_factory=SettingsSnapshot)
    system_snapshot: SystemSnapshot = field(default_factory=SystemSnapshot)
    workspace_os: WorkspaceOsSnapshot = field(default_factory=WorkspaceOsSnapshot)
    last_event_topic: str = ""
    last_event_source: str = ""
    settings_version: int = 0
    last_command: str = ""
    last_command_intent: str = ""
    active_chat_request_id: str = ""
    last_chat_request_id: str = ""
    chat_status: str = "idle"
    chat_streaming: bool = False
    chat_stream_buffer: str = ""
    chat_stream_revision: int = 0
    chat_pending_user_text: str = ""
    chat_started_user_text: str = ""
    chat_context_sources: tuple[str, ...] = ()
    chat_token_estimate: int = 0
    last_assistant_message: str = ""
    chat_history_count: int = 0
    chat_history_messages: tuple[ChatHistoryMessage, ...] = ()
    chat_history_revision: int = 0
    last_chat_error: str = ""
    chat_workspace_entity_id: str = ""
    chat_workspace_entity_type: str = ""
    chat_workspace_entity_title: str = ""
    chat_workspace_entity_description: str = ""
    chat_workspace_entity_url: str = ""
    chat_workspace_entity_path: str = ""
    chat_active_session_key: str = "default"
    errors: tuple[str, ...] = ()

    # Track 3.2 — full projection of feature catalogs
    notes_catalog: tuple[NoteItem, ...] = ()
    note_selected: NoteItem | None = None
    note_index_status: tuple[int, int] = ()  # (files, ms)
    memory_catalog: tuple[MemoryItem, ...] = ()
    memory_selected: tuple[str, ...] = ()
    plugin_catalog: tuple[PluginItem, ...] = ()

    # Track R7 — agent / workflow run projections
    agent_runs: tuple[AgentRunItem, ...] = ()
    workflow_runs: tuple[WorkflowRunItem, ...] = ()
    active_agent_run_id: str = ""
    active_workflow_run_id: str = ""
    pending_permission_check: PermissionCheckItem | None = None
    permission_check_revision: int = 0
Reducer = Callable[[AppState, Event], AppState]


def _freeze_metadata(raw: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, dict):
        return ()
    return tuple(
        (str(k), str(v)) for k, v in raw.items() if v is not None
    )


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


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


def _coerce_float(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _settings_from_payload(payload: dict[str, Any]) -> SettingsSnapshot:
    return SettingsSnapshot(
        theme=str(payload.get("theme", "dark")),
        accent=str(payload.get("accent", "#3B82F6")),
        default_model=str(payload.get("default_model", "llama3.2:3b")),
        summarize_model=str(payload.get("summarize_model", "llama3.2:3b")),
        ollama_url=str(payload.get("ollama_url", "http://localhost:11434")),
        hotkey=str(payload.get("hotkey", "alt+space")),
        low_memory_mode=_coerce_bool(payload.get("low_memory_mode", False)),
        window_width=_coerce_int(payload.get("window_width", 1100), 1100),
        window_height=_coerce_int(payload.get("window_height", 700), 700),
        window_alpha=_coerce_float(payload.get("window_alpha", 0.95), 0.95),
        obsidian_vault_path=str(payload.get("obsidian_vault_path", "")),
        overlay_mode=str(payload.get("overlay_mode", "palette")),
        model_name=str(payload.get("model_name", "llama3.2:3b")),
        provider=str(payload.get("provider", "ollama")),
        openai_base_url=str(payload.get("openai_base_url", "https://api.openai.com/v1")),
        openai_api_key=str(payload.get("openai_api_key", "")),
        vault_path=str(payload.get("vault_path", "")),
        overlay_hotkey=str(payload.get("overlay_hotkey", "alt+space")),
        telemetry_enabled=_coerce_bool(payload.get("telemetry_enabled", True)),
        schema_version=_coerce_int(payload.get("schema_version", 1), 1),
    )


def _reduce_service_state(state: AppState, event: Event) -> AppState:
    if event.topic != SERVICE_STATE_CHANGED:
        return state
    name = str(event.payload.get("name", ""))
    new_state = str(event.payload.get("state", "off"))
    detail = str(event.payload.get("detail", ""))
    updated = {s.name: s for s in state.services}
    updated[name] = ServiceSnapshot(name=name, state=new_state, detail=detail)
    services = tuple(sorted(updated.values(), key=lambda s: s.name))
    return replace(
        state,
        services=services,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_settings_changed(state: AppState, event: Event) -> AppState:
    if event.topic != SETTINGS_CHANGED:
        return state
    return replace(
        state,
        settings_version=state.settings_version + 1,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_settings_snapshot(state: AppState, event: Event) -> AppState:
    if event.topic != SETTINGS_SNAPSHOT:
        return state
    return replace(
        state,
        settings=_settings_from_payload(event.payload),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


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


def _reduce_command_routed(state: AppState, event: Event) -> AppState:
    if event.topic != COMMAND_ROUTED:
        return state
    text = str(event.payload.get("text", ""))
    pending = text if _is_pending_chat_user_text(text) else ""
    return replace(
        state,
        last_command=text,
        last_command_intent=str(event.payload.get("intent", "")),
        chat_pending_user_text=pending,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_chat_started(state: AppState, event: Event) -> AppState:
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


def _reduce_chat_chunk(state: AppState, event: Event) -> AppState:
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


def _reduce_chat_complete(state: AppState, event: Event) -> AppState:
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


def _reduce_chat_cancelled(state: AppState, event: Event) -> AppState:
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


def _reduce_chat_error(state: AppState, event: Event) -> AppState:
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


def _reduce_chat_history_loaded(state: AppState, event: Event) -> AppState:
    if event.topic != CHAT_HISTORY_LOADED:
        return state
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


def _reduce_context_snapshot(state: AppState, event: Event) -> AppState:
    if event.topic != CONTEXT_SNAPSHOT_CREATED:
        return state
    raw_sources = event.payload.get("sources", [])
    sources = tuple(str(item) for item in raw_sources) if isinstance(raw_sources, (list, tuple)) else ()
    tokens = _coerce_int(event.payload.get("context_size_tokens", 0), 0)
    return replace(
        state,
        chat_context_sources=sources,
        chat_token_estimate=tokens,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_error(state: AppState, event: Event) -> AppState:
    if event.topic != APP_ERROR:
        return state
    message = str(event.payload.get("message", "unknown error"))
    errors = state.errors + (message,)
    if len(errors) > 20:
        errors = errors[-20:]
    return replace(
        state,
        errors=errors,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_phase(state: AppState, event: Event) -> AppState:
    if event.topic != APP_PHASE:
        return state
    phase = str(event.payload.get("phase", state.phase))
    return replace(
        state,
        phase=phase,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_system_snapshot(state: AppState, event: Event) -> AppState:
    if event.topic != SYSTEM_SNAPSHOT:
        return state
    payload = dict(event.payload)
    snapshot = SystemSnapshot(
        phase=str(payload.get("phase", state.system_snapshot.phase)),
        cpu_percent=float(payload.get("cpu_percent", state.system_snapshot.cpu_percent)),
        ram_percent=float(payload.get("ram_percent", state.system_snapshot.ram_percent)),
        ollama_online=bool(payload.get("ollama_online", state.system_snapshot.ollama_online)),
        service_states=tuple(payload.get("service_states", state.system_snapshot.service_states)),
        tool_count=int(payload.get("tool_count", state.system_snapshot.tool_count)),
        recent_commands=tuple(payload.get("recent_commands", state.system_snapshot.recent_commands)),
        event_rate=float(payload.get("event_rate", state.system_snapshot.event_rate)),
        uptime=float(payload.get("uptime", state.system_snapshot.uptime)),
        extra=dict(payload.get("extra", state.system_snapshot.extra)),
    )
    return replace(
        state,
        system_snapshot=snapshot,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _entity_session_key(entity_type: str, entity_id: str) -> str:
    return f"entity:{entity_type}:{entity_id}"


def _clear_chat_entity_fields(state: AppState, event: Event) -> AppState:
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


def _reduce_chat_workspace_entity(state: AppState, event: Event) -> AppState:
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


def _reduce_ui_chat_new_session(state: AppState, event: Event) -> AppState:
    """Clear sticky workspace entity context when user starts a fresh chat."""
    if event.topic != UI_CHAT_NEW_SESSION:
        return state
    return _clear_chat_entity_fields(state, event)


def _reduce_workspace_os_event(state: AppState, event: Event) -> AppState:
    """Update Workspace OS counters, recent events, and entity list."""
    current = state.workspace_os
    if event.topic == EVENT_ENTITY_CREATED:
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
    elif event.topic == EVENT_ENTITY_UPDATED:
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
    elif event.topic == EVENT_ENTITY_DELETED:
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


def _reduce_note_results(state: AppState, event: Event) -> AppState:
    """Project note search results into AppState."""
    if event.topic != NOTE_SEARCH_RESULTS:
        return state
    raw_results = event.payload.get("results") or []
    items: list[NoteItem] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        items.append(
            NoteItem(
                path=str(item.get("path", "")),
                title=str(item.get("title", "")),
                snippet=str(item.get("snippet", "")),
            )
        )
    return replace(
        state,
        notes_catalog=tuple(items),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_note_selected(state: AppState, event: Event) -> AppState:
    """Project selected note preview into AppState."""
    if event.topic != NOTE_SELECTED:
        return state
    selected = NoteItem(
        path=str(event.payload.get("path", "")),
        title=str(event.payload.get("title", "")),
        snippet=str(event.payload.get("body", "")),
    )
    return replace(
        state,
        note_selected=selected,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_note_created(state: AppState, event: Event) -> AppState:
    """Append newly created note to the catalog."""
    if event.topic != NOTE_CREATED:
        return state
    path = str(event.payload.get("path", ""))
    item = NoteItem(path=path, title=path, snippet="")
    return replace(
        state,
        notes_catalog=(item,) + state.notes_catalog,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_note_index_complete(state: AppState, event: Event) -> AppState:
    """Record note indexing status."""
    if event.topic != NOTE_INDEX_COMPLETE:
        return state
    files = int(event.payload.get("files", 0))
    ms = int(event.payload.get("ms", 0))
    return replace(
        state,
        note_index_status=(files, ms),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_memory_stored(state: AppState, event: Event) -> AppState:
    """Append newly stored memory to the catalog."""
    if event.topic != MEMORY_STORED:
        return state
    item = MemoryItem(
        node_id=str(event.payload.get("id", "")),
        label=str(event.payload.get("label", "")),
    )
    return replace(
        state,
        memory_catalog=(item,) + state.memory_catalog,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_memory_selected(state: AppState, event: Event) -> AppState:
    """Project selected memory labels into AppState."""
    if event.topic != MEMORY_SELECTED:
        return state
    labels = event.payload.get("labels")
    if isinstance(labels, (list, tuple)):
        selected = tuple(str(label) for label in labels)
    else:
        selected = ()
    return replace(
        state,
        memory_selected=selected,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_memory_cleared(state: AppState, event: Event) -> AppState:
    """Handle memory selection clear or node deletion."""
    if event.topic != MEMORY_CLEARED:
        return state
    node_id = str(event.payload.get("id", ""))
    if node_id:
        catalog = tuple(item for item in state.memory_catalog if item.node_id != node_id)
        return replace(
            state,
            memory_catalog=catalog,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    return replace(
        state,
        memory_selected=(),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_plugin_catalog(state: AppState, event: Event) -> AppState:
    """Project plugin catalog into AppState."""
    if event.topic != PLUGIN_CATALOG:
        return state
    raw_plugins = event.payload.get("plugins") or []
    items: list[PluginItem] = []
    for plugin in raw_plugins:
        if not isinstance(plugin, dict):
            continue
        items.append(
            PluginItem(
                plugin_id=str(plugin.get("id", "")),
                name=str(plugin.get("name", "")),
                description=str(plugin.get("description", "")),
                kind=str(plugin.get("kind", "extension")),
                enabled=bool(plugin.get("enabled", True)),
                error=str(plugin.get("error", "")),
                pending_restart=bool(plugin.get("pending_restart", False)),
            )
        )
    return replace(
        state,
        plugin_catalog=tuple(items),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_plugin_state_changed(state: AppState, event: Event) -> AppState:
    """Update enabled flag for a plugin in the catalog."""
    if event.topic != PLUGIN_STATE_CHANGED:
        return state
    plugin_id = str(event.payload.get("id", ""))
    enabled = bool(event.payload.get("enabled", True))
    updated = tuple(
        replace(item, enabled=enabled) if item.plugin_id == plugin_id else item
        for item in state.plugin_catalog
    )
    return replace(
        state,
        plugin_catalog=updated,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _find_agent_run(runs: tuple[AgentRunItem, ...], agent_id: str) -> AgentRunItem | None:
    for run in runs:
        if run.agent_id == agent_id:
            return run
    return None


def _upsert_agent_run(runs: tuple[AgentRunItem, ...], item: AgentRunItem) -> tuple[AgentRunItem, ...]:
    filtered = tuple(r for r in runs if r.agent_id != item.agent_id)
    updated = (item,) + filtered
    if len(updated) > _MAX_RUN_FEED:
        updated = updated[:_MAX_RUN_FEED]
    return updated


def _find_workflow_run(runs: tuple[WorkflowRunItem, ...], run_id: str) -> WorkflowRunItem | None:
    for run in runs:
        if run.run_id == run_id:
            return run
    return None


def _upsert_workflow_run(
    runs: tuple[WorkflowRunItem, ...], item: WorkflowRunItem
) -> tuple[WorkflowRunItem, ...]:
    filtered = tuple(r for r in runs if r.run_id != item.run_id)
    updated = (item,) + filtered
    if len(updated) > _MAX_RUN_FEED:
        updated = updated[:_MAX_RUN_FEED]
    return updated


def _reduce_agent_run(state: AppState, event: Event) -> AppState:
    """Project agent lifecycle events into agent_runs feed."""
    if event.topic not in {
        AGENT_SPAWNED,
        AGENT_TASK_REQUEST,
        AGENT_TASK_COMPLETE,
        AGENT_TERMINATED,
    }:
        return state

    payload = event.payload
    agent_id = str(payload.get("agent_id", ""))
    if not agent_id:
        return state

    existing = _find_agent_run(state.agent_runs, agent_id)
    request_id = str(payload.get("request_id") or (existing.request_id if existing else ""))
    task = str(payload.get("task") or (existing.task if existing else ""))
    steps = _coerce_int(payload.get("steps"), existing.steps if existing else 0)
    workspace_id = str(
        payload.get("workspace_id") or (existing.workspace_id if existing else "")
    )
    if event.topic == AGENT_TERMINATED:
        error = str(payload.get("error", ""))
    else:
        error = str(payload.get("error") or (existing.error if existing else ""))

    if event.topic == AGENT_SPAWNED:
        run_state = str(payload.get("state", "spawning"))
        item = AgentRunItem(
            agent_id=agent_id,
            request_id=request_id,
            state=run_state,
            task=task,
            workspace_id=workspace_id,
        )
        return replace(
            state,
            agent_runs=_upsert_agent_run(state.agent_runs, item),
            active_agent_run_id=agent_id,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if existing is None:
        existing = AgentRunItem(agent_id=agent_id, request_id=request_id)

    if event.topic == AGENT_TASK_REQUEST:
        run_state = "running"
        steps = existing.steps + 1
    elif event.topic == AGENT_TASK_COMPLETE:
        run_state = "waiting"
    elif event.topic == AGENT_TERMINATED:
        run_state = "failed" if error else "terminated"
    else:
        run_state = existing.state

    item = AgentRunItem(
        agent_id=agent_id,
        request_id=request_id,
        state=run_state,
        task=task or existing.task,
        error=error,
        steps=steps if steps else existing.steps,
        workspace_id=workspace_id or existing.workspace_id,
    )
    active_id = state.active_agent_run_id
    if event.topic == AGENT_TERMINATED and active_id == agent_id:
        active_id = ""

    return replace(
        state,
        agent_runs=_upsert_agent_run(state.agent_runs, item),
        active_agent_run_id=active_id,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_workflow_run(state: AppState, event: Event) -> AppState:
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


def _reduce_permission_check(state: AppState, event: Event) -> AppState:
    """Project interactive permission checks for UI approval flow."""
    if event.topic == PERMISSION_CHECK_REQUEST:
        payload = event.payload
        if not payload.get("interactive"):
            return state
        check_id = str(payload.get("check_id", ""))
        if not check_id:
            return state
        perms = tuple(str(p) for p in (payload.get("permissions") or []) if p)
        item = PermissionCheckItem(
            check_id=check_id,
            permissions=perms,
            actor_type=str(payload.get("actor_type", "agent")),
            actor_id=str(payload.get("actor_id") or ""),
            summary=str(payload.get("summary") or "An agent requested supervised permissions."),
            interactive=True,
        )
        return replace(
            state,
            pending_permission_check=item,
            permission_check_revision=state.permission_check_revision + 1,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if event.topic == PERMISSION_CHECK_RESULT:
        result_id = str(event.payload.get("check_id", ""))
        pending = state.pending_permission_check
        if pending is None or pending.check_id != result_id:
            return state
        return replace(
            state,
            pending_permission_check=None,
            permission_check_revision=state.permission_check_revision + 1,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    return state


_DEFAULT_REDUCERS: tuple[Reducer, ...] = (
    _reduce_service_state,
    _reduce_settings_changed,
    _reduce_settings_snapshot,
    _reduce_command_routed,
    _reduce_chat_started,
    _reduce_chat_chunk,
    _reduce_chat_complete,
    _reduce_chat_cancelled,
    _reduce_chat_error,
    _reduce_chat_history_loaded,
    _reduce_context_snapshot,
    _reduce_error,
    _reduce_phase,
    _reduce_system_snapshot,
    _reduce_chat_workspace_entity,
    _reduce_ui_chat_new_session,
    _reduce_workspace_os_event,
    _reduce_note_results,
    _reduce_note_selected,
    _reduce_note_created,
    _reduce_note_index_complete,
    _reduce_memory_stored,
    _reduce_memory_selected,
    _reduce_memory_cleared,
    _reduce_plugin_catalog,
    _reduce_plugin_state_changed,
    _reduce_agent_run,
    _reduce_workflow_run,
    _reduce_permission_check,
)


class AppStateStore:
    """
    Holds current AppState; applies reducers on bus events.
    UI reads snapshots; never mutates services directly.
    """

    def __init__(self, bus: EventBus, reducers: tuple[Reducer, ...] | None = None) -> None:
        self._bus = bus
        self._reducers = reducers or _DEFAULT_REDUCERS
        self._lock = threading.RLock()
        self._state = AppState()
        self._listeners: list[Callable[[AppState], None]] = []
        self._unsubscribers: list[Callable[[], None]] = []
        for topic in APP_STATE_TOPICS:
            self._unsubscribers.append(bus.subscribe(topic, self._on_event))

    @property
    def snapshot(self) -> AppState:
        with self._lock:
            return self._state

    def subscribe(self, listener: Callable[[AppState], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    def _on_event(self, event: Event) -> None:
        listeners: list[Callable[[AppState], None]] = []
        new_state = self._state
        with self._lock:
            for reducer in self._reducers:
                new_state = reducer(new_state, event)
            if new_state != self._state:
                self._state = new_state
                listeners = list(self._listeners)

        if not listeners:
            return

        for listener in listeners:
            try:
                listener(new_state)
            except Exception as exc:
                logger.exception("AppState listener failed for topic=%s", event.topic)
                try:
                    self._bus.publish(
                        APP_ERROR,
                        {
                            "message": f"AppState listener failed: {exc}",
                            "topic": event.topic,
                        },
                        source="app_state",
                    )
                except Exception:
                    logger.exception("Failed to publish app.error for listener failure")

    def close(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
