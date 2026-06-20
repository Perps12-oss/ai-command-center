"""Central application state — updated only via event reducers."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    APP_ERROR,
    APP_PHASE,
    COMMAND_ROUTED,
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
    APP_ERROR,
    APP_PHASE,
    SYSTEM_SNAPSHOT,
)


@dataclass(frozen=True, slots=True)
class ServiceSnapshot:
    name: str
    state: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class AppState:
    """Immutable snapshot of application state."""

    phase: str = "idle"
    services: tuple[ServiceSnapshot, ...] = ()
    settings: SettingsSnapshot = field(default_factory=SettingsSnapshot)
    system_snapshot: SystemSnapshot = field(default_factory=SystemSnapshot)
    last_event_topic: str = ""
    last_event_source: str = ""
    settings_version: int = 0
    last_command: str = ""
    last_command_intent: str = ""
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


_DEFAULT_REDUCERS: tuple[Reducer, ...] = (
    _reduce_service_state,
    _reduce_settings_changed,
    _reduce_settings_snapshot,
    _reduce_command_routed,
    _reduce_error,
    _reduce_phase,
    _reduce_system_snapshot,
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
        with self._lock:
            new_state = self._state
            for reducer in self._reducers:
                new_state = reducer(new_state, event)
            if new_state != self._state:
                self._state = new_state
                listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(new_state)
            except Exception:
                continue

    def close(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
