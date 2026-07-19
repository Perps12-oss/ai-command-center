"""Tri-state execution authority decision contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DecisionKind(str, Enum):
    """Authority classification — chat is never an implicit fallback."""

    ACTIONABLE = "actionable"
    CONVERSATIONAL = "conversational"
    AMBIGUOUS = "ambiguous"
    LEGACY_ROUTE = "legacy_route"


@dataclass(frozen=True, slots=True)
class ExecutionDecision:
    """Outcome of ExecutionAuthority intent analysis."""

    kind: DecisionKind
    text: str
    capability: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    legacy_intent: str = ""
    reason: str = ""
    skip_planner: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "capability": self.capability,
            "args": dict(self.args),
            "legacy_intent": self.legacy_intent,
            "reason": self.reason,
            "skip_planner": self.skip_planner,
        }
