"""Execution domain model — unified Execution dataclass.

This is the canonical domain object for a single execution run,
combining chat, orchestration, and agent pipeline data.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ExecutionStatus(str, Enum):
    """Lifecycle status of an execution run."""

    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


@dataclass
class Execution:
    """Unified execution run record.

    Created from ORCHESTRATION_RUN_SNAPSHOT, CHAT_COMPLETE, or agent events.
    """

    run_id: str = ""
    request_id: str = ""
    source: str = "chat"          # "chat" | "orchestration" | "agent" | "workflow"
    status: ExecutionStatus = ExecutionStatus.PENDING
    query: str = ""
    intent: str = ""
    provider_id: str = ""
    model: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    duration_ms: int = 0
    tokens_used: int = 0
    response_source: str = ""
    truth_valid: bool = False
    truth_detail: str = ""
    error: str = ""
    trace_id: str = ""
    span_id: str = ""
    receipt_id: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        if self.duration_ms:
            return self.duration_ms / 1000
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return 0.0

    @property
    def short_summary(self) -> str:
        text = self.intent or self.query
        if len(text) > 60:
            return text[:57] + "…"
        return text or "(no summary)"

    @classmethod
    def from_orchestration_payload(cls, payload: dict) -> "Execution":
        return cls(
            run_id=str(payload.get("request_id", "")),
            request_id=str(payload.get("request_id", "")),
            source="orchestration",
            status=ExecutionStatus.COMPLETED,
            query=str(payload.get("query", "")),
            intent=str(payload.get("intent", "")),
            provider_id=str(payload.get("provider_id", "")),
            model=str(payload.get("model", "")),
            response_source=str(payload.get("response_source", "")),
            truth_valid=bool(payload.get("truth_valid", False)),
            truth_detail=str(payload.get("truth_detail", "")),
            trace_id=str(payload.get("trace_id", "")),
            span_id=str(payload.get("span_id", "")),
            receipt_id=str(payload.get("receipt_id", "")),
        )
