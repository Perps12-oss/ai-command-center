"""Central application state — updated only via event reducers."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from ai_command_center.core.event_bus import Event, EventBus

APP_STATE_TOPICS: tuple[str, ...] = (
    "service.state_changed",
    "settings.changed",
    "settings.snapshot",
    "command.routed",
    "app.error",
    "app.phase",
    "workspace.resolved",
)


@dataclass(frozen=True, slots=True)
class ServiceSnapshot:
    name: str
    state: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    """UI-consumable settings projection from settings.snapshot events."""

    theme: str = "dark"
    accent: str = "#3B82F6"
    default_model: str = "llama3.2:3b"
    summarize_model: str = "llama3.2:3b"
    ollama_url: str = "http://localhost:11434"
    hotkey: str = "alt+space"
    low_memory_mode: str = "false"
    window_width: str = "1100"
    window_height: str = "700"
    obsidian_vault_path: str = ""
    overlay_mode: str = "palette"


@dataclass(frozen=True, slots=True)
class SuggestionSnapshot:
    """UI-consumable pre-AI suggestion projection."""

    label: str
    command: str
    score: float = 0.0


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    """UI-consumable active-workspace projection from workspace.resolved events."""

    workspace_id: str = ""
    title: str = ""
    inferred_task: str = ""
    confidence: float = 0.0
    evidence_source: str = "none"
    suggestions: tuple[SuggestionSnapshot, ...] = ()


@dataclass(frozen=True, slots=True)
class AppState:
    """Immutable snapshot of application state."""

    phase: str = "idle"
    services: tuple[ServiceSnapshot, ...] = ()
    settings: SettingsSnapshot = SettingsSnapshot()
    last_event_topic: str = ""
    last_event_source: str = ""
    settings_version: int = 0
    last_command: str = ""
    last_command_intent: str = ""
    workspace: WorkspaceSnapshot = WorkspaceSnapshot()
    errors: tuple[str, ...] = ()


Reducer = Callable[[AppState, Event], AppState]


def _settings_from_payload(payload: dict[str, Any]) -> SettingsSnapshot:
    return SettingsSnapshot(
        theme=str(payload.get("theme", "dark")),
        accent=str(payload.get("accent", "#3B82F6")),
        default_model=str(payload.get("default_model", "llama3.2:3b")),
        summarize_model=str(payload.get("summarize_model", "llama3.2:3b")),
        ollama_url=str(payload.get("ollama_url", "http://localhost:11434")),
        hotkey=str(payload.get("hotkey", "alt+space")),
        low_memory_mode=str(payload.get("low_memory_mode", "false")),
        window_width=str(payload.get("window_width", "1100")),
        window_height=str(payload.get("window_height", "700")),
        obsidian_vault_path=str(payload.get("obsidian_vault_path", "")),
        overlay_mode=str(payload.get("overlay_mode", "palette")),
    )


def _reduce_service_state(state: AppState, event: Event) -> AppState:
    if event.topic != "service.state_changed":
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
    if event.topic != "settings.changed":
        return state
    return replace(
        state,
        settings_version=state.settings_version + 1,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_settings_snapshot(state: AppState, event: Event) -> AppState:
    if event.topic != "settings.snapshot":
        return state
    return replace(
        state,
        settings=_settings_from_payload(event.payload),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_command_routed(state: AppState, event: Event) -> AppState:
    if event.topic != "command.routed":
        return state
    return replace(
        state,
        last_command=str(event.payload.get("text", "")),
        last_command_intent=str(event.payload.get("intent", "")),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_error(state: AppState, event: Event) -> AppState:
    if event.topic != "app.error":
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


def _reduce_workspace_resolved(state: AppState, event: Event) -> AppState:
    if event.topic != "workspace.resolved":
        return state
    raw_suggestions = event.payload.get("suggestions") or ()
    suggestions = tuple(
        SuggestionSnapshot(
            label=str(item.get("label", "")),
            command=str(item.get("command", "")),
            score=float(item.get("score", 0.0)),
        )
        for item in raw_suggestions
        if isinstance(item, dict)
    )
    workspace = WorkspaceSnapshot(
        workspace_id=str(event.payload.get("workspace_id", "")),
        title=str(event.payload.get("title", "")),
        inferred_task=str(event.payload.get("inferred_task", "")),
        confidence=float(event.payload.get("confidence", 0.0)),
        evidence_source=str(event.payload.get("evidence_source", "none")),
        suggestions=suggestions,
    )
    return replace(
        state,
        workspace=workspace,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_phase(state: AppState, event: Event) -> AppState:
    if event.topic != "app.phase":
        return state
    phase = str(event.payload.get("phase", state.phase))
    return replace(
        state,
        phase=phase,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


_DEFAULT_REDUCERS: tuple[Reducer, ...] = (
    _reduce_service_state,
    _reduce_settings_changed,
    _reduce_settings_snapshot,
    _reduce_command_routed,
    _reduce_workspace_resolved,
    _reduce_error,
    _reduce_phase,
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
