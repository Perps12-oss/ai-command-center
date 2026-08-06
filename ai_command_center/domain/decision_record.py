"""Decision Record — primary explainability surface (ADR-021).

Evidence + Policy + Receipts + Verification. Not model CoT/scratchpad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.domain.world_model import utc_now


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """Grounded explanation of why an action was allowed, denied, or escalated."""

    record_id: str
    run_id: str = ""
    step_id: str = ""
    capability: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    receipt: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    created_at: str = field(default_factory=lambda: utc_now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "capability": self.capability,
            "evidence": dict(self.evidence),
            "policy": dict(self.policy),
            "receipt": dict(self.receipt),
            "verification": dict(self.verification),
            "summary": self.summary,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionRecord:
        return cls(
            record_id=str(data.get("record_id", "")),
            run_id=str(data.get("run_id", "")),
            step_id=str(data.get("step_id", "")),
            capability=str(data.get("capability", "")),
            evidence=dict(data.get("evidence") or {}),
            policy=dict(data.get("policy") or {}),
            receipt=dict(data.get("receipt") or {}),
            verification=dict(data.get("verification") or {}),
            summary=str(data.get("summary", "")),
            created_at=str(data.get("created_at") or utc_now().isoformat()),
        )


__all__ = ["DecisionRecord"]
