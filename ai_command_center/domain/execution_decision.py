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


@dataclass(frozen=True, slots=True)
class ExecutionDecision:
    """Outcome of ExecutionAuthority intent analysis."""

    kind: DecisionKind
    text: str
    capability: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    skip_planner: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "capability": self.capability,
            "args": dict(self.args),
            "reason": self.reason,
            "skip_planner": self.skip_planner,
        }
