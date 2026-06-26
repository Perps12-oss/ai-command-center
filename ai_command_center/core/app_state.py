"""Central application state — updated only via event reducers."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from ai_command_center.core.event_bus import (
    EVENT_ACTION_REGISTERED,
    EVENT_ENTITY_CREATED,
    EVENT_RELATIONSHIP_CREATED,
    EVENT_TIMELINE_EVENT,
    Event,
    EventBus,
)
from ai_command_center.core.events.topics import (
    APP_ERROR,
    APP_PHASE,
    CHAT_CANCELLED,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CHAT_STARTED,
    COMMAND_ROUTED,
    CONTEXT_SNAPSHOT_CREATED,
    SERVICE_STATE_CHANGED,
    SETTINGS_CHANGED,
    SETTINGS_SNAPSHOT,
    SYSTEM_SNAPSHOT,
)
from ai_command_center.domain.settings_snapshot import SettingsSnapshot
from ai_command_center.domain.system_snapshot import SystemSnapshot

APP_STATE_TOPICS: tuple[str, ...] = (
    SERVICE_STATE_CHANGED,
    SETTINGS_CHANGED,
    SETTINGS_SNAPSHOT,
    COMMAND_ROUTED,
    CHAT_STARTED,
    CHAT_COMPLETE,
    CHAT_CANCELLED,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CONTEXT_SNAPSHOT_CREATED,
    APP_ERROR,
    APP_PHASE,
    SYSTEM_SNAPSHOT,
    # Workspace OS (Track B - Phase 2)
    EVENT_ENTITY_CREATED,
    EVENT_RELATIONSHIP_CREATED,
    EVENT_ACTION_REGISTERED,
    EVENT_TIMELINE_EVENT,
)


@dataclass(frozen=True, slots=True)
class ServiceSnapshot:
    name: str
    state: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceOsSnapshot:
    """Minimal Workspace OS projection for the inspector UI."""

    entity_count: int = 0
    relationship_count: int = 0
    action_count: int = 0
    event_count: int = 0
    recent_events: tuple[str, ...] = ()


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
    chat_context_sources: tuple[str, ...] = ()
    chat_token_estimate: int = 0
    last_assistant_message: str = ""
    chat_history_count: int = 0
    last_chat_error: str = ""
    errors: tuple[str, ...] = ()


Reducer = Callable[[AppState, Event], AppState]


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


def _reduce_command_routed(state: AppState, event: Event) -> AppState:
    if event.topic != COMMAND_ROUTED:
        return state
    return replace(
        state,
        last_command=str(event.payload.get("text", "")),
        last_command_intent=str(event.payload.get("intent", "")),
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
        last_chat_error="",
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
        last_chat_error=str(event.payload.get("message", "Unknown error")),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_chat_history_loaded(state: AppState, event: Event) -> AppState:
    if event.topic != CHAT_HISTORY_LOADED:
        return state
    messages = event.payload.get("messages")
    count = len(messages) if isinstance(messages, list) else state.chat_history_count
    return replace(
        state,
        chat_history_count=count,
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


def _reduce_workspace_os_event(state: AppState, event: Event) -> AppState:
    """Increment Workspace OS counters and recent events from event stream."""
    current = state.workspace_os
    if event.topic == EVENT_ENTITY_CREATED:
        snapshot = replace(current, entity_count=current.entity_count + 1)
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


_DEFAULT_REDUCERS: tuple[Reducer, ...] = (
    _reduce_service_state,
    _reduce_settings_changed,
    _reduce_settings_snapshot,
    _reduce_command_routed,
    _reduce_chat_started,
    _reduce_chat_complete,
    _reduce_chat_cancelled,
    _reduce_chat_error,
    _reduce_chat_history_loaded,
    _reduce_context_snapshot,
    _reduce_error,
    _reduce_phase,
    _reduce_system_snapshot,
    _reduce_workspace_os_event,
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
            except Exception:
                continue

    def close(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
