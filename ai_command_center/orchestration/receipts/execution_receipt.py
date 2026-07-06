"""Mandatory execution receipt contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    """Immutable proof that an orchestration provider ran."""

    receipt_id: str
    request_id: str
    intent: str
    provider_id: str
    success: bool
    facts: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "intent": self.intent,
            "provider_id": self.provider_id,
            "success": self.success,
            "facts": dict(self.facts),
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }
