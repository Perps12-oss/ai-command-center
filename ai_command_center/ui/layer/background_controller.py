"""Background modulation from EventBus — global state only."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import OLLAMA_STATUS, SYSTEM_SNAPSHOT, TELEMETRY_EVENT
from ai_command_center.ui.layer.background_spec import load_background_layer

if TYPE_CHECKING:
    from ai_command_center.ui.layer.background_canvas import BackgroundCanvas

_FLICKER_MAX_HZ = 0.5


class BackgroundController:
    """Maps system state to background tint — never per-component."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._bindings = load_background_layer().get("modulation_bindings", {})
        self._canvas: BackgroundCanvas | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._last_flicker = 0.0
        self._health_map = {
            "healthy": 0,
            "degraded": 1,
            "stressed": 2,
            "unknown": 3,
        }

    def attach(self, canvas: BackgroundCanvas | None) -> None:
        self._canvas = canvas
        if canvas is not None:
            self._apply_defaults()

    def start(self) -> None:
        for topic in (SYSTEM_SNAPSHOT, OLLAMA_STATUS, TELEMETRY_EVENT):
            self._unsubs.append(self._bus.subscribe(topic, self._on_event))

    def stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _apply_defaults(self) -> None:
        if self._canvas is not None:
            self._canvas.set_modulation(tint_step=1)

    def _on_event(self, event: Event) -> None:
        if self._canvas is None:
            return
        if event.topic == SYSTEM_SNAPSHOT:
            health = str(event.payload.get("health", "unknown"))
            step = self._health_map.get(health, 1)
            cpu = float(event.payload.get("cpu_percent", 0))
            if cpu > 85:
                step = min(3, step + 1)
            self._canvas.set_modulation(tint_step=step)
        elif event.topic == OLLAMA_STATUS:
            online = bool(event.payload.get("online"))
            self._canvas.set_modulation(desaturate=not online, dim=0.0 if online else 0.25)
        elif event.topic == TELEMETRY_EVENT:
            now = time.monotonic()
            if now - self._last_flicker < 1.0 / _FLICKER_MAX_HZ:
                return
            self._last_flicker = now
            self._canvas.set_modulation(flicker=0.03)
