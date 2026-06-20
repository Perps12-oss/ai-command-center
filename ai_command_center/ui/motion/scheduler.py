"""EventBus-driven motion signals for live UI primitives."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import CHAT_COMPLETE, CHAT_STARTED, COMMAND_HISTORY, OLLAMA_STATUS, SYSTEM_EVENTS, SYSTEM_SNAPSHOT, TELEMETRY_EVENTS, UI_COMMAND, NOTE_INDEX_PROGRESS

_MAX_UPDATES_PER_SEC = 30


@dataclass(slots=True)
class MotionSignal:
    primitive_id: str
    intensity: float
    rate: float
    payload: dict[str, Any] = field(default_factory=dict)


class MotionScheduler:
    """Maps EventBus topics to normalized motion signals — no decorative loops."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._listeners: list[Callable[[MotionSignal], None]] = []
        self._unsubs: list[Callable[[], None]] = []
        self._last_emit = 0.0
        self._min_interval = 1.0 / _MAX_UPDATES_PER_SEC
        self._cpu = 0.0
        self._ram = 0.0
        self._event_count = 0
        self._last_event_ts = 0.0

    def subscribe(self, listener: Callable[[MotionSignal], None]) -> None:
        self._listeners.append(listener)

    def start(self) -> None:
        topics = (
            SYSTEM_SNAPSHOT,
            TELEMETRY_EVENTS,
            COMMAND_HISTORY,
            UI_COMMAND,
            CHAT_STARTED,
            CHAT_COMPLETE,
            NOTE_INDEX_PROGRESS,
            OLLAMA_STATUS,
        )
        for topic in topics:
            self._unsubs.append(self._bus.subscribe(topic, self._on_event))

    def stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _on_event(self, event: Event) -> None:
        now = time.monotonic()
        if now - self._last_emit < self._min_interval:
            return
        self._last_emit = now

        if event.topic == SYSTEM_SNAPSHOT:
            self._cpu = float(event.payload.get("cpu_percent", 0))
            self._ram = float(event.payload.get("ram_percent", 0))
            rate = max(0.5, min(2.0, 0.5 + self._cpu / 100.0))
            self._emit("SystemHeartbeat", self._cpu / 100.0, rate, event.payload)
            self._emit("HeroPanel", self._cpu / 100.0, rate, event.payload)
            self._emit("StatusFluxBarGrid", self._ram / 100.0, rate, event.payload)

        elif event.topic in (TELEMETRY_EVENTS, SYSTEM_EVENTS):
            self._event_count += 1
            elapsed = max(0.1, now - self._last_event_ts) if self._last_event_ts else 1.0
            self._last_event_ts = now
            glow = min(1.0, self._event_count / 20.0)
            self._emit("EventStreamRibbon", glow, 1.0, event.payload)
            self._emit("ActivityPulseField", glow, 1.5, event.payload)
            self._emit("HeroPanel", glow, 1.0, {"glow_intensity": glow})

        elif event.topic in (COMMAND_HISTORY, UI_COMMAND):
            self._emit("CommandFlowTrail", 1.0, 2.0, event.payload)

        elif event.topic in (CHAT_STARTED, CHAT_COMPLETE):
            self._emit("ActivityPulse", 0.8, 3.0, event.payload)

        elif event.topic == NOTE_INDEX_PROGRESS:
            self._emit("ActivityPulse", 0.5, 1.0, event.payload)

        elif event.topic == OLLAMA_STATUS:
            online = bool(event.payload.get("online"))
            self._emit("StatusPill", 1.0 if online else 0.2, 0.5, event.payload)

    def _emit(
        self,
        primitive_id: str,
        intensity: float,
        rate: float,
        payload: dict[str, Any],
    ) -> None:
        signal = MotionSignal(
            primitive_id=primitive_id,
            intensity=max(0.0, min(1.0, intensity)),
            rate=rate,
            payload=dict(payload),
        )
        for listener in self._listeners:
            listener(signal)
