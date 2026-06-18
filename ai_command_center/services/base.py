"""Base service contract — load / hibernate / unload."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ai_command_center.services.states import ServiceState

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus


class BaseService(ABC):
    """All services implement demand-based lifecycle hooks."""

    name: str = "base"

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._state = ServiceState.OFF

    @property
    def state(self) -> ServiceState:
        return self._state

    def _set_state(self, state: ServiceState, detail: str = "") -> None:
        self._state = state
        self._bus.publish(
            "service.state_changed",
            {"name": self.name, "state": state.value, "detail": detail},
            source=self.name,
        )

    def load(self) -> None:
        if self._state in {ServiceState.IDLE, ServiceState.ACTIVE}:
            return
        self._on_load()
        self._set_state(ServiceState.IDLE, "loaded")

    def hibernate(self) -> None:
        if self._state == ServiceState.OFF:
            return
        self._on_hibernate()
        self._set_state(ServiceState.HIBERNATED, "hibernated")

    def unload(self) -> None:
        if self._state == ServiceState.OFF:
            return
        self._on_unload()
        self._set_state(ServiceState.OFF, "unloaded")

    def activate(self) -> None:
        if self._state == ServiceState.OFF:
            self.load()
        self._on_activate()
        self._set_state(ServiceState.ACTIVE, "active")

    @abstractmethod
    def _on_load(self) -> None: ...

    def _on_hibernate(self) -> None:
        pass

    def _on_unload(self) -> None:
        pass

    def _on_activate(self) -> None:
        pass
