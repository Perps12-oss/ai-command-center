"""Append-only execution run record for time-travel diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionRun:
    """Immutable snapshot of a completed orchestration or chat run."""

    run_id: str
    request_id: str
    source: str
    snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "source": self.source,
            "snapshot": dict(self.snapshot),
            "created_at": self.created_at,
        }
