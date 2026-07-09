"""Execution run state — approved plan steps with lifecycle status."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionStepStatus(str, Enum):
    """Lifecycle status for a single execution run step."""

    PENDING = "pending"
    STARTED = "started"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskTier(str, Enum):
    """Capability risk tier driving approval gates."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Static fallback when catalog metadata is absent.
_CAPABILITY_RISK: dict[str, RiskTier] = {
    "create_note": RiskTier.LOW,
    "note.create": RiskTier.LOW,
    "search_files": RiskTier.LOW,
    "create_task": RiskTier.LOW,
    "create_entity": RiskTier.MEDIUM,
    "modify_file": RiskTier.MEDIUM,
    "send_email": RiskTier.MEDIUM,
    "delete_file": RiskTier.HIGH,
    "git_push": RiskTier.HIGH,
    "shell": RiskTier.HIGH,
}


def capability_risk_for(capability: str) -> RiskTier:
    """Static fallback risk for a capability name."""
    return _CAPABILITY_RISK.get(capability, RiskTier.MEDIUM)


def resolve_risk_tier(
    capability: str,
    *,
    catalog_risk: str = "",
    require_approval: bool = False,
) -> RiskTier:
    """Resolve risk from catalog metadata, plan flag, or static map."""
    normalized = str(catalog_risk or "").strip().lower()
    if normalized in {tier.value for tier in RiskTier}:
        tier = RiskTier(normalized)
    else:
        tier = capability_risk_for(capability)
    if require_approval and tier == RiskTier.LOW:
        return RiskTier.MEDIUM
    return tier


def needs_approval_gate(tier: RiskTier) -> bool:
    """Low-tier steps auto-run; medium and high require explicit approval."""
    return tier != RiskTier.LOW


@dataclass(frozen=True, slots=True)
class ExecutionRunStep:
    """Single step within an active execution run."""

    step_id: str
    capability: str
    args: dict[str, Any] = field(default_factory=dict)
    status: ExecutionStepStatus = ExecutionStepStatus.PENDING
    risk: str = RiskTier.LOW.value
    require_approval: bool = False
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "step_id": self.step_id,
            "capability": self.capability,
            "args": dict(self.args),
            "status": self.status.value,
            "risk": self.risk,
            "require_approval": self.require_approval,
        }
        if self.result is not None:
            payload["result"] = dict(self.result)
        if self.error:
            payload["error"] = self.error
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionRunStep:
        raw_status = str(data.get("status", ExecutionStepStatus.PENDING.value))
        try:
            status = ExecutionStepStatus(raw_status)
        except ValueError:
            status = ExecutionStepStatus.PENDING
        raw_result = data.get("result")
        result = dict(raw_result) if isinstance(raw_result, dict) else None
        return cls(
            step_id=str(data.get("step_id", "")),
            capability=str(data.get("capability", "")),
            args=dict(data.get("args") or {}),
            status=status,
            risk=str(data.get("risk", RiskTier.LOW.value)),
            require_approval=bool(data.get("require_approval", False)),
            result=result,
            error=str(data.get("error") or "") or None,
        )
