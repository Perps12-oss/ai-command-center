"""Intention contract — planner capability intent (ADR-018).

An Intention is the canonical unit between Planner and Orchestrator.
The LLM never emits executable tool calls; it may only assist the planner
in producing Intentions that map to PlanStep / TOOL_INVOKE via the orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_command_center.domain.planner_plan import PlanStep


@dataclass(frozen=True, slots=True)
class Intention:
    """Capability intention owned by the planner catalog, not by the model."""

    capability: str
    args: dict[str, Any] = field(default_factory=dict)
    require_approval: bool = False
    step_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "args": dict(self.args),
            "require_approval": self.require_approval,
            "step_id": self.step_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Intention:
        return cls(
            capability=str(data.get("capability", "")).strip(),
            args=dict(data.get("args") or {}),
            require_approval=bool(data.get("require_approval", False)),
            step_id=str(data.get("step_id", "")),
        )

    @classmethod
    def from_plan_step(cls, step: PlanStep) -> Intention:
        return cls(
            capability=step.capability.strip(),
            args=dict(step.args),
            require_approval=bool(step.require_approval),
            step_id=step.step_id,
        )

    def to_plan_step(self) -> PlanStep:
        return PlanStep(
            step_id=self.step_id or "step-1",
            capability=self.capability,
            args=dict(self.args),
            require_approval=self.require_approval,
        )


__all__ = ["Intention"]
