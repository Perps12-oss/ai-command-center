"""Composite autonomy confidence (ADR-022).

Policy / Evidence / Verification / Execution — not token logprobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True, slots=True)
class AutonomyScore:
    """Composite score used to decide auto-execute vs escalate (hard policy still wins)."""

    policy_confidence: float
    evidence_confidence: float
    verification_confidence: float
    execution_confidence: float
    aggregate: float = 0.0
    escalate: bool = False
    reason: str = ""

    def __post_init__(self) -> None:
        # frozen dataclass: use object.__setattr__
        pc = _clamp(self.policy_confidence)
        ec = _clamp(self.evidence_confidence)
        vc = _clamp(self.verification_confidence)
        xc = _clamp(self.execution_confidence)
        agg = round((pc + ec + vc + xc) / 4.0, 4)
        object.__setattr__(self, "policy_confidence", pc)
        object.__setattr__(self, "evidence_confidence", ec)
        object.__setattr__(self, "verification_confidence", vc)
        object.__setattr__(self, "execution_confidence", xc)
        object.__setattr__(self, "aggregate", agg)

    @classmethod
    def compute(
        cls,
        *,
        policy_confidence: float,
        evidence_confidence: float,
        verification_confidence: float,
        execution_confidence: float,
        threshold: float = 0.6,
        hard_policy_block: bool = False,
        reason: str = "",
    ) -> AutonomyScore:
        score = cls(
            policy_confidence=policy_confidence,
            evidence_confidence=evidence_confidence,
            verification_confidence=verification_confidence,
            execution_confidence=execution_confidence,
            reason=reason,
        )
        escalate = hard_policy_block or score.aggregate < threshold
        object.__setattr__(score, "escalate", escalate)
        if hard_policy_block and not reason:
            object.__setattr__(score, "reason", "hard_policy_block")
        elif escalate and not reason:
            object.__setattr__(score, "reason", "aggregate_below_threshold")
        return score

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_confidence": self.policy_confidence,
            "evidence_confidence": self.evidence_confidence,
            "verification_confidence": self.verification_confidence,
            "execution_confidence": self.execution_confidence,
            "aggregate": self.aggregate,
            "escalate": self.escalate,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutonomyScore:
        return cls.compute(
            policy_confidence=float(data.get("policy_confidence", 0.0) or 0.0),
            evidence_confidence=float(data.get("evidence_confidence", 0.0) or 0.0),
            verification_confidence=float(data.get("verification_confidence", 0.0) or 0.0),
            execution_confidence=float(data.get("execution_confidence", 0.0) or 0.0),
            threshold=float(data.get("threshold", 0.6) or 0.6),
            hard_policy_block=bool(data.get("hard_policy_block", False)),
            reason=str(data.get("reason", "")),
        )


__all__ = ["AutonomyScore"]
