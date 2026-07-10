"""Correlation context shared by Brain events, logs, journal entries, and results."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    """Trace context propagated through a goal/action lifecycle."""

    correlation_id: str
    goal_id: str = ""
    action_id: str = ""

    @classmethod
    def new(cls, *, goal_id: str = "", action_id: str = "") -> CorrelationContext:
        return cls(correlation_id=uuid.uuid4().hex, goal_id=goal_id, action_id=action_id)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> CorrelationContext:
        raw = payload.get("correlation")
        if isinstance(raw, dict):
            return cls(
                correlation_id=str(raw.get("correlation_id") or uuid.uuid4().hex),
                goal_id=str(raw.get("goal_id") or payload.get("goal_id") or ""),
                action_id=str(raw.get("action_id") or payload.get("action_id") or ""),
            )
        return cls(
            correlation_id=str(payload.get("correlation_id") or uuid.uuid4().hex),
            goal_id=str(payload.get("goal_id") or ""),
            action_id=str(payload.get("action_id") or ""),
        )

    def with_goal(self, goal_id: str) -> CorrelationContext:
        return CorrelationContext(self.correlation_id, goal_id, self.action_id)

    def with_action(self, action_id: str) -> CorrelationContext:
        return CorrelationContext(self.correlation_id, self.goal_id, action_id)

    def to_payload(self) -> dict[str, str]:
        return {
            "correlation_id": self.correlation_id,
            "goal_id": self.goal_id,
            "action_id": self.action_id,
        }
