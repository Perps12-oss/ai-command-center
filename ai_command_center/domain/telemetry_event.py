"""Canonical telemetry event contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    event_type: str
    payload: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    emitted_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def timestamp(self) -> str:
        when = self.emitted_at
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return when.isoformat()

    def payload_dict(self) -> dict[str, Any]:
        return dict(self.payload)

    @classmethod
    def from_row(cls, event_type: str, timestamp: str, payload: dict[str, Any]) -> "TelemetryEvent":
        try:
            emitted = datetime.fromisoformat(timestamp)
        except ValueError:
            emitted = datetime.now(timezone.utc)
        return cls(
            event_type=event_type,
            payload=tuple(payload.items()),
            emitted_at=emitted,
        )
