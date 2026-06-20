"""Telemetry service placeholder."""

from __future__ import annotations

from ai_command_center.domain.telemetry_event import TelemetryEvent


class TelemetryService:
    """Publishes telemetry events through the event bus when wired in."""

    def __init__(self) -> None:
        self._events: list[TelemetryEvent] = []

    def capture(self, event: TelemetryEvent) -> TelemetryEvent:
        self._events.append(event)
        return event

    def list(self) -> list[TelemetryEvent]:
        return list(self._events)
