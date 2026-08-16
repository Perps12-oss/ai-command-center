"""Decision Record — primary explainability surface (ADR-021).

Evidence + Policy + Receipts + Verification. Not model CoT/scratchpad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.domain.world_model import utc_now

MISSING_MARKER = "__missing__"


def grounded_mapping(value: Any) -> dict[str, Any]:
    """Normalize a Decision Record section. Never omit the key; never use `{}` as missing."""
    if value is None or value == MISSING_MARKER:
        return {"status": MISSING_MARKER}
    if isinstance(value, dict):
        if not value:
            return {"status": MISSING_MARKER}
        return dict(value)
    return {"value": value}


def is_missing(value: Any) -> bool:
    if value == MISSING_MARKER:
        return True
    if isinstance(value, dict) and value.get("status") == MISSING_MARKER:
        return True
    return False


def format_missing_visible(value: Any) -> str:
    """Operator-visible missing evidence — never a blank success."""
    if is_missing(value):
        return "missing"
    if value is None:
        return "missing"
    if isinstance(value, dict):
        return str(value)
    return str(value)


def should_mount_decision_card(*, actor_type: str, pending: bool) -> bool:
    """DecisionCard is conditional: pending intention approval only (ADR-021 M5)."""
    return bool(pending) and str(actor_type) == "intention"


def reasoning_copy(record: dict[str, Any] | None, *, fallback: str) -> str:
    """Mission Control Reasoning binds Decision Record fields, not mode prose alone."""
    if not record:
        return fallback
    summary = str(record.get("summary") or "").strip()
    if not summary or summary == MISSING_MARKER:
        text = fallback
    else:
        text = summary
    missing_keys = [
        key
        for key in ("evidence", "policy", "receipt", "verification")
        if is_missing(record.get(key))
    ]
    if missing_keys:
        text = f"{text} · missing: {', '.join(missing_keys)}"
    return text[:120]


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
            "evidence": grounded_mapping(self.evidence),
            "policy": grounded_mapping(self.policy),
            "receipt": grounded_mapping(self.receipt),
            "verification": grounded_mapping(self.verification),
            "summary": self.summary if self.summary else MISSING_MARKER,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionRecord:
        return cls(
            record_id=str(data.get("record_id", "")),
            run_id=str(data.get("run_id", "")),
            step_id=str(data.get("step_id", "")),
            capability=str(data.get("capability", "")),
            evidence=grounded_mapping(data.get("evidence")),
            policy=grounded_mapping(data.get("policy")),
            receipt=grounded_mapping(data.get("receipt")),
            verification=grounded_mapping(data.get("verification")),
            summary=str(data.get("summary", "")),
            created_at=str(data.get("created_at") or utc_now().isoformat()),
        )


__all__ = [
    "DecisionRecord",
    "MISSING_MARKER",
    "format_missing_visible",
    "grounded_mapping",
    "is_missing",
    "reasoning_copy",
    "should_mount_decision_card",
]
