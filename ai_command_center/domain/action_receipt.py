"""ActionReceipt domain stub — immutable receipt for an executed action.

Linked to orchestration receipts, tool executions, and agent steps.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActionReceipt:
    """Immutable receipt for a completed (or failed) action.

    Used by the Artifact OS and audit log to record what happened.
    """

    receipt_id: str = ""
    action_type: str = ""           # "tool" | "chat" | "agent_step" | "workflow_step"
    actor_id: str = ""              # who performed the action
    timestamp: float = field(default_factory=time.time)
    request_id: str = ""
    run_id: str = ""
    success: bool = True
    error: str = ""
    inputs: tuple[tuple[str, str], ...] = ()
    outputs: tuple[tuple[str, str], ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_dict(cls, d: dict) -> "ActionReceipt":
        inputs = tuple((str(k), str(v)) for k, v in (d.get("inputs") or {}).items())
        outputs = tuple((str(k), str(v)) for k, v in (d.get("outputs") or {}).items())
        metadata = tuple((str(k), str(v)) for k, v in (d.get("metadata") or {}).items())
        return cls(
            receipt_id=str(d.get("receipt_id", "")),
            action_type=str(d.get("action_type", "")),
            actor_id=str(d.get("actor_id", "")),
            timestamp=float(d.get("timestamp", time.time())),
            request_id=str(d.get("request_id", "")),
            run_id=str(d.get("run_id", "")),
            success=bool(d.get("success", True)),
            error=str(d.get("error", "")),
            inputs=inputs,
            outputs=outputs,
            metadata=metadata,
        )
