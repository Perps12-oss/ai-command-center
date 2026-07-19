"""System monitor — publishes system.snapshot and system.events (read-only)."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import COMMAND_HISTORY, COMMAND_ROUTED, OLLAMA_STATUS, OPENAI_STATUS, SYSTEM_EVENTS, SYSTEM_SNAPSHOT, UI_COMMAND
from ai_command_center.services.base import BaseService

_POLL_INTERVAL_S = 2.0
_HISTORY_LEN = 50


class SystemMonitorService(BaseService):
    name = "system_monitor"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._events: deque[dict] = deque(maxlen=_HISTORY_LEN)
        self._prev_cpu = 0.0
        self._prev_ram = 0.0
        self._command_count = 0
        self._unsubs: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubs.append(
            self._bus.subscribe(UI_COMMAND, self._on_command)
        )
        self._unsubs.append(
            self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed)
        )
        self._unsubs.append(
            self._bus.subscribe(OLLAMA_STATUS, self._on_ollama_status)
        )
        self._unsubs.append(
            self._bus.subscribe(OPENAI_STATUS, self._on_openai_status)
        )
        self._ollama_online = False
        self._openai_online = False
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._poll_loop, name="system-monitor", daemon=True
        )
        self._thread.start()
        self._publish_history()

    def _on_unload(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _on_ollama_status(self, event: Event) -> None:
        self._ollama_online = bool(event.payload.get("online"))

    def _on_openai_status(self, event: Event) -> None:
        self._openai_online = bool(event.payload.get("online"))

    def _on_command(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if text:
            self._record_event("command", text[:80])

    def _on_command_routed(self, event: Event) -> None:
        from ai_command_center.core.routing_authority import is_routing_authority

        if not is_routing_authority(event.source):
            return
        intent = str(event.payload.get("intent", ""))
        self._command_count += 1
        self._record_event("routed", intent)
        self._publish_history()

    def _record_event(self, kind: str, detail: str) -> None:
        self._events.append(
            {
                "kind": kind,
                "detail": detail,
                "ts": time.time(),
            }
        )
        self._bus.publish(
            SYSTEM_EVENTS,
            {"kind": kind, "detail": detail, "ts": time.time()},
            source=self.name,
        )

    def _publish_history(self) -> None:
        self._bus.publish(
            COMMAND_HISTORY,
            {
                "commands": list(self._events)[-20:],
                "total": self._command_count,
            },
            source=self.name,
        )

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._publish_snapshot()
            except Exception:
                pass
            self._stop.wait(_POLL_INTERVAL_S)

    def _publish_snapshot(self) -> None:
        cpu = 0.0
        ram = 0.0
        try:
            import psutil

            cpu = float(psutil.cpu_percent(interval=None))
            ram = float(psutil.virtual_memory().percent)
        except Exception:
            cpu = self._prev_cpu
            ram = self._prev_ram

        health = "healthy"
        if cpu > 90 or ram > 90:
            health = "stressed"
        elif not self._ollama_online:
            health = "degraded"

        model_load = min(100.0, cpu * 0.6 + (10.0 if self._ollama_online else 0.0))

        self._bus.publish(
            SYSTEM_SNAPSHOT,
            {
                "cpu_percent": round(cpu, 1),
                "ram_percent": round(ram, 1),
                "model_load": round(model_load, 1),
                "network": 0.0,
                "health": health,
                "ollama_online": self._ollama_online,
                "cpu_delta": round(cpu - self._prev_cpu, 1),
                "ram_delta": round(ram - self._prev_ram, 1),
                "extra": {"openai_online": self._openai_online},
                "eventbus_topic_counts": self._bus.get_topic_counts(),
            },
            source=self.name,
        )
        self._prev_cpu = cpu
        self._prev_ram = ram
