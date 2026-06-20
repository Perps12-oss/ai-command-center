"""Base service contract — load / hibernate / unload."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ai_command_center.core.events.topics import (
    SERVICE_ERROR,
    SERVICE_READY,
    SERVICE_STARTED,
    SERVICE_STATE_CHANGED,
    SERVICE_STOPPED,
)
from ai_command_center.services.states import ServiceState

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus


class BaseService(ABC):
    """All services implement demand-based lifecycle hooks."""

    name: str = "base"

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._state = ServiceState.STOPPED

    @property
    def state(self) -> ServiceState:
        return self._state

    def get_state(self) -> str:
        return self._state.value

    def _set_state(self, state: ServiceState, detail: str = "") -> None:
        self._state = state
        self._bus.publish(
            SERVICE_STATE_CHANGED,
            {"name": self.name, "state": state.value, "detail": detail},
            source=self.name,
        )

    def start(self) -> None:
        if self._state in {ServiceState.READY, ServiceState.ACTIVE, ServiceState.IDLE}:
            return
        self._set_state(ServiceState.STARTING, "starting")
        self.load()
        self.activate()
        self._set_state(ServiceState.READY, "ready")
        self._bus.publish(SERVICE_STARTED, {"service": self.name}, source=self.name)
        self._bus.publish(SERVICE_READY, {"service": self.name}, source=self.name)

    def stop(self) -> None:
        if self._state == ServiceState.STOPPED:
            return
        self._set_state(ServiceState.STOPPING, "stopping")
        self.hibernate()
        self.unload()
        self._set_state(ServiceState.STOPPED, "stopped")
        self._bus.publish(SERVICE_STOPPED, {"service": self.name}, source=self.name)

    def load(self) -> None:
        if self._state in {ServiceState.IDLE, ServiceState.ACTIVE, ServiceState.READY}:
            return
        self._on_load()
        self._set_state(ServiceState.IDLE, "loaded")

    def hibernate(self) -> None:
        if self._state == ServiceState.STOPPED:
            return
        self._on_hibernate()
        self._set_state(ServiceState.HIBERNATED, "hibernated")

    def unload(self) -> None:
        if self._state == ServiceState.STOPPED:
            return
        self._on_unload()
        self._set_state(ServiceState.STOPPED, "unloaded")

    def activate(self) -> None:
        if self._state == ServiceState.STOPPED:
            self.load()
        self._on_activate()
        self._set_state(ServiceState.ACTIVE, "active")

    def fail(self, detail: str = "error") -> None:
        self._set_state(ServiceState.ERROR, detail)
        self._bus.publish(SERVICE_ERROR, {"service": self.name, "detail": detail}, source=self.name)

    @abstractmethod
    def _on_load(self) -> None: ...

    def _on_hibernate(self) -> None:
        pass

    def _on_unload(self) -> None:
        pass

    def _on_activate(self) -> None:
        pass
