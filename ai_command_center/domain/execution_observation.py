"""Execution step observation — facts for replan (ADR-019).

Distinct from observer-framework ``Observation`` (filesystem/clipboard signals).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.domain.world_model import utc_now


@dataclass(frozen=True, slots=True)
class ExecutionObservation:
    """Structured result of one orchestrator step for World-Model-grounded replan."""

    run_id: str
    step_id: str
    step_index: int
    capability: str
    args: dict[str, Any] = field(default_factory=dict)
    success: bool = False
    output: str = ""
    error: str = ""
    invariants: tuple[str, ...] = ()
    invariant_status: str = ""
    observed_at: str = field(default_factory=lambda: utc_now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "step_index": self.step_index,
            "capability": self.capability,
            "args": dict(self.args),
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "invariants": list(self.invariants),
            "invariant_status": self.invariant_status,
            "observed_at": self.observed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionObservation:
        raw_inv = data.get("invariants") or ()
        invariants = tuple(str(x) for x in raw_inv)
        return cls(
            run_id=str(data.get("run_id", "")),
            step_id=str(data.get("step_id", "")),
            step_index=int(data.get("step_index", 0) or 0),
            capability=str(data.get("capability", "")),
            args=dict(data.get("args") or {}),
            success=bool(data.get("success", False)),
            output=str(data.get("output", "")),
            error=str(data.get("error", "")),
            invariants=invariants,
            invariant_status=str(data.get("invariant_status", "")),
            observed_at=str(data.get("observed_at") or utc_now().isoformat()),
        )


__all__ = ["ExecutionObservation"]
