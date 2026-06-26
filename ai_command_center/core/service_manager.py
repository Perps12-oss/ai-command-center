"""Service registry and lifecycle orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import APP_PHASE
from ai_command_center.services.states import ServiceState

if TYPE_CHECKING:
    from ai_command_center.services.base import BaseService


class ServiceManager:
    """Registers services and coordinates load / hibernate / unload."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._services: dict[str, BaseService] = {}

    def register(self, service: BaseService) -> None:
        if service.name in self._services:
            raise ValueError(f"service already registered: {service.name}")
        self._services[service.name] = service

    def get(self, name: str) -> BaseService | None:
        return self._services.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._services))

    def load_all(self) -> None:
        for service in self._ordered():
            service.start()

    def hibernate_all(self) -> None:
        for service in reversed(self._ordered()):
            service.stop()

    def unload_all(self) -> None:
        for service in reversed(self._ordered()):
            service.stop()

    def shutdown(self) -> None:
        """Unload everything — no background services remain."""
        self.unload_all()
        self._bus.publish(APP_PHASE, {"phase": "shutdown"}, source="service_manager")

    def _ordered(self) -> Iterable[BaseService]:
        return self._services.values()

    def any_active(self) -> bool:
        return any(s.state == ServiceState.ACTIVE for s in self._services.values())

    def any_loaded(self) -> bool:
        return any(s.state != ServiceState.STOPPED for s in self._services.values())
