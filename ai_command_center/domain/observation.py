"""Observer contracts for raw external signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.world_model import utc_now


class ObservationSource(str, Enum):
    FILESYSTEM = "filesystem"
    CLIPBOARD = "clipboard"
    NOTIFICATION = "notification"
    OTHER = "other"


class ObservationMode(str, Enum):
    STARTUP_SYNC = "startup_sync"
    CONTINUOUS = "continuous"


class ObservationChangeType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    MOVED = "moved"
    SNAPSHOT = "snapshot"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Observation:
    id: str
    source: ObservationSource
    mode: ObservationMode
    subject: str
    change_type: ObservationChangeType
    raw_payload: dict[str, Any] = field(default_factory=dict)
    correlation: CorrelationContext = field(default_factory=CorrelationContext.new)
    observed_at: str = field(default_factory=lambda: utc_now().isoformat())

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value,
            "mode": self.mode.value,
            "observed_at": self.observed_at,
            "subject": self.subject,
            "change_type": self.change_type.value,
            "raw_payload": dict(self.raw_payload),
            "correlation": self.correlation.to_payload(),
        }
