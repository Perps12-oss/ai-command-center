"""Append-only execution run record for time-travel diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.domain.correlation import CorrelationContext


@dataclass(frozen=True, slots=True)
class ExecutionRun:
    """Immutable snapshot of a completed orchestration or chat run."""

    run_id: str
    request_id: str
    source: str
    snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    correlation: CorrelationContext = field(default_factory=CorrelationContext.new)

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "source": self.source,
            "snapshot": dict(self.snapshot),
            "created_at": self.created_at,
            "correlation_id": self.correlation.correlation_id,
        }
