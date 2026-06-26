"""Base service contract — canonical lifecycle per AGENTS.md v4.

Lifecycle states: STOPPED → STARTING → READY | DEGRADED | ERROR → STOPPING → STOPPED.
Services publish state changes via SERVICE_STATE_CHANGED and the explicit
milestones SERVICE_STARTED, SERVICE_READY, SERVICE_STOPPED, SERVICE_ERROR.
"""

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
    """All services implement the canonical STARTING/READY/ERROR/STOPPING lifecycle."""

    name: str = "base"

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._state = ServiceState.STOPPED

    @property
    def state(self) -> ServiceState:
        return self._state

    def get_state(self) -> str:
        """Return the canonical service state string."""
        return self._state.value

    def _set_state(self, state: ServiceState, detail: str = "") -> None:
        """Update internal state and publish a state-change event."""
        self._state = state
        self._bus.publish(
            SERVICE_STATE_CHANGED,
            {"name": self.name, "state": state.value, "detail": detail},
            source=self.name,
        )

    def load(self) -> None:
        """Deprecated alias for start(); kept for verification scripts."""
        self.start()

    def unload(self) -> None:
        """Deprecated alias for stop(); kept for verification scripts."""
        self.stop()

    def start(self) -> None:
        """Start the service if it is not already ready or running."""
        if self._state in {ServiceState.READY, ServiceState.STARTING}:
            return
        if self._state == ServiceState.ERROR:
            # Allow restart from error state.
            pass
        self._set_state(ServiceState.STARTING, "starting")
        try:
            self._on_load()
        except Exception as exc:
            self._set_state(ServiceState.ERROR, str(exc))
            self._bus.publish(
                SERVICE_ERROR,
                {"service": self.name, "detail": str(exc)},
                source=self.name,
            )
            return
        self._set_state(ServiceState.READY, "ready")
        self._bus.publish(SERVICE_STARTED, {"service": self.name}, source=self.name)
        self._bus.publish(SERVICE_READY, {"service": self.name}, source=self.name)

    def stop(self) -> None:
        """Stop the service if it is not already stopped."""
        if self._state == ServiceState.STOPPED:
            return
        self._set_state(ServiceState.STOPPING, "stopping")
        try:
            self._on_unload()
        except Exception as exc:
            self._bus.publish(
                SERVICE_ERROR,
                {"service": self.name, "detail": str(exc)},
                source=self.name,
            )
        self._set_state(ServiceState.STOPPED, "stopped")
        self._bus.publish(SERVICE_STOPPED, {"service": self.name}, source=self.name)

    def degrade(self, detail: str = "degraded") -> None:
        """Mark the service as degraded but still operational."""
        if self._state != ServiceState.READY:
            return
        self._set_state(ServiceState.DEGRADED, detail)

    def fail(self, detail: str = "error") -> None:
        """Mark the service as failed."""
        self._set_state(ServiceState.ERROR, detail)
        self._bus.publish(
            SERVICE_ERROR,
            {"service": self.name, "detail": detail},
            source=self.name,
        )

    @abstractmethod
    def _on_load(self) -> None:
        """One-time setup; subscribe to topics and allocate resources."""

    def _on_unload(self) -> None:
        """Teardown; unsubscribe and release resources."""
