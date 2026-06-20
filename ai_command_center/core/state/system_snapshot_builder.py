"""System snapshot builder that emits canonical system state events."""

from __future__ import annotations

from typing import Any

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import SYSTEM_SNAPSHOT
from ai_command_center.domain.system_snapshot import SystemSnapshot

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore


class SystemSnapshotBuilder:
    """Builds and publishes a normalized system snapshot."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def publish(self, *, state_store: AppStateStore | None = None, extra: dict[str, Any] | None = None) -> None:
        snapshot = self.build(state_store=state_store, extra=extra)
        self._bus.publish(SYSTEM_SNAPSHOT, snapshot.__dict__, source="system_snapshot_builder")
        return None

    def build(self, *, state_store: AppStateStore | None = None, extra: dict[str, Any] | None = None) -> SystemSnapshot:
        cpu_percent = 0.0
        ram_percent = 0.0
        if psutil is not None:
            try:
                cpu_percent = float(psutil.cpu_percent(interval=None))
                ram_percent = float(psutil.virtual_memory().percent)
            except Exception:
                cpu_percent = 0.0
                ram_percent = 0.0

        services = ()
        if state_store is not None:
            services = tuple((service.name, service.state) for service in state_store.snapshot.services)

        payload = {
            "phase": "ready",
            "cpu_percent": cpu_percent,
            "ram_percent": ram_percent,
            "ollama_online": False,
            "service_states": services,
            "tool_count": 0,
            "recent_commands": (),
            "event_rate": 0.0,
            "uptime": 0.0,
        }
        if extra:
            payload.update(extra)
        return SystemSnapshot(**payload)
