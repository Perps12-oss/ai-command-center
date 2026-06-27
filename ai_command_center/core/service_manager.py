"""Service registry and lifecycle orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import APP_PHASE, SERVICE_RESTART_REQUEST
from ai_command_center.services.states import ServiceState

if TYPE_CHECKING:
    from ai_command_center.services.base import BaseService


class ServiceManager:
    """Registers services and coordinates start/stop lifecycle.

    Listens to `service.restart_request` so that other services (e.g. the
    plugin registry) can ask for a service restart without calling this manager
    directly.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._services: dict[str, BaseService] = {}
        self._unsubscribe_restart: Callable[[], None] | None = None

    def register(self, service: BaseService) -> None:
        if service.name in self._services:
            raise ValueError(f"service already registered: {service.name}")
        self._services[service.name] = service

    def get(self, name: str) -> BaseService | None:
        return self._services.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._services))

    def load_all(self) -> None:
        self._subscribe_restart()
        for service in self._ordered():
            service.start()

    def unload_all(self) -> None:
        if self._unsubscribe_restart is not None:
            self._unsubscribe_restart()
            self._unsubscribe_restart = None
        for service in reversed(self._ordered()):
            service.stop()

    def shutdown(self) -> None:
        """Stop all services — no background services remain."""
        self.unload_all()
        self._bus.publish(APP_PHASE, {"phase": "shutdown"}, source="service_manager")

    def _subscribe_restart(self) -> None:
        if self._unsubscribe_restart is None:
            self._unsubscribe_restart = self._bus.subscribe(
                SERVICE_RESTART_REQUEST, self._on_restart_request
            )

    def _on_restart_request(self, event: Event) -> None:
        name = str(event.payload.get("service", "")).strip()
        if not name:
            return
        service = self._services.get(name)
        if service is None:
            self._bus.publish(
                APP_PHASE,
                {"phase": "error", "message": f"unknown service: {name}"},
                source="service_manager",
            )
            return
        service.stop()
        service.start()

    def _ordered(self) -> list[BaseService]:
        return list(self._services.values())

    def any_ready(self) -> bool:
        return any(s.state == ServiceState.READY for s in self._services.values())

    def any_loaded(self) -> bool:
        return any(s.state != ServiceState.STOPPED for s in self._services.values())

    def any_active(self) -> bool:
        """Deprecated alias for any_ready()."""
        return self.any_ready()
