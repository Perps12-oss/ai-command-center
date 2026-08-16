"""Composite autonomy confidence (ADR-022).

Policy / Evidence / Verification / Execution — not token logprobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ADR-022 §11 — binding band edges. Settings must not silently retune these.
BAND_HIGH_MAX = 0.4
BAND_MEDIUM_MAX = 0.7


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def confidence_band(aggregate: float) -> str:
    """Return high / medium / low for an aggregate score (ADR-022 §11)."""
    score = _clamp(aggregate)
    if score < BAND_HIGH_MAX:
        return "high"
    if score < BAND_MEDIUM_MAX:
        return "medium"
    return "low"


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
    band: str = "low"

    def __post_init__(self) -> None:
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
        object.__setattr__(self, "band", confidence_band(agg))

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
        # ``threshold`` is retained for call-site compatibility; bands replace it.
        del threshold
        score = cls(
            policy_confidence=policy_confidence,
            evidence_confidence=evidence_confidence,
            verification_confidence=verification_confidence,
            execution_confidence=execution_confidence,
            reason=reason,
        )
        escalate = hard_policy_block or score.band == "high"
        object.__setattr__(score, "escalate", escalate)
        if hard_policy_block and not reason:
            object.__setattr__(score, "reason", "hard_policy_block")
        elif escalate and not reason:
            object.__setattr__(score, "reason", "aggregate_high_hitl_band")
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
            "band": self.band,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutonomyScore:
        return cls.compute(
            policy_confidence=float(data.get("policy_confidence", 0.0) or 0.0),
            evidence_confidence=float(data.get("evidence_confidence", 0.0) or 0.0),
            verification_confidence=float(data.get("verification_confidence", 0.0) or 0.0),
            execution_confidence=float(data.get("execution_confidence", 0.0) or 0.0),
            hard_policy_block=bool(data.get("hard_policy_block", False)),
            reason=str(data.get("reason", "")),
        )


__all__ = [
    "AutonomyScore",
    "BAND_HIGH_MAX",
    "BAND_MEDIUM_MAX",
    "confidence_band",
]
