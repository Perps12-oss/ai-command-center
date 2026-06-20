"""Canonical telemetry event contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    event_type: str
    payload: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    emitted_at: datetime = field(default_factory=datetime.utcnow)
