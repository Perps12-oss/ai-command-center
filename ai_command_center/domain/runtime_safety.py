"""Runtime safety contracts for approved Brain actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.world_model import utc_now


class SecurityTier(str, Enum):
    READ = "read"
    WRITE = "write"
    WRITE_DESTROY = "write_destroy"


class ActionStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DENIED = "denied"
    TIMED_OUT = "timed_out"


class RuntimeErrorCode(str, Enum):
    VALIDATION_ERROR = "validation_error"
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_TIMEOUT = "approval_timeout"
    PERMISSION_ERROR = "permission_error"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    EXECUTION_FAILED = "execution_failed"
    WORLD_MODEL_APPLY_FAILED = "world_model_apply_failed"
    TRANSIENT_IO = "transient_io"


class RetryHint(str, Enum):
    NONE = "none"
    RETRY_SAME = "retry_same"
    RETRY_AFTER_DELAY = "retry_after_delay"
    REVISE_GOAL = "revise_goal"
    REQUEST_APPROVAL = "request_approval"


@dataclass(frozen=True, slots=True)
class RuntimeErrorRecord:
    code: RuntimeErrorCode
    message: str
    retry_hint: RetryHint = RetryHint.NONE
    details: dict[str, Any] = field(default_factory=dict)
    correlation: CorrelationContext = field(default_factory=CorrelationContext.new)

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "retry_hint": self.retry_hint.value,
            "details": dict(self.details),
            "correlation": self.correlation.to_payload(),
        }


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    id: str
    action_id: str
    tier: SecurityTier
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 60
    correlation: CorrelationContext = field(default_factory=CorrelationContext.new)

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "tier": self.tier.value,
            "summary": self.summary,
            "details": dict(self.details),
            "timeout_seconds": self.timeout_seconds,
            "correlation": self.correlation.to_payload(),
        }


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    approval_id: str
    approved: bool
    reason: str
    decided_at: datetime = field(default_factory=utc_now)
    correlation: CorrelationContext = field(default_factory=CorrelationContext.new)

    def to_payload(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "approved": self.approved,
            "reason": self.reason,
            "decided_at": self.decided_at.isoformat(),
            "correlation": self.correlation.to_payload(),
        }


@dataclass(frozen=True, slots=True)
class ActionResult:
    action_id: str
    status: ActionStatus
    output: dict[str, Any] = field(default_factory=dict)
    error: RuntimeErrorRecord | None = None
    correlation: CorrelationContext = field(default_factory=CorrelationContext.new)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action_id": self.action_id,
            "status": self.status.value,
            "output": dict(self.output),
            "correlation": self.correlation.to_payload(),
        }
        if self.error is not None:
            payload["error"] = self.error.to_payload()
        return payload
