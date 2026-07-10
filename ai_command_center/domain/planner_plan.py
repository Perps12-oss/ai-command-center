"""Planner execution manifest — goal to capability DAG, no execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PlanStep:
    """Single planned capability invocation."""

    step_id: str
    capability: str
    args: dict[str, Any] = field(default_factory=dict)
    require_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "capability": self.capability,
            "args": dict(self.args),
            "require_approval": self.require_approval,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanStep:
        return cls(
            step_id=str(data.get("step_id", "")),
            capability=str(data.get("capability", "")),
            args=dict(data.get("args") or {}),
            require_approval=bool(data.get("require_approval", False)),
        )


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Validated plan manifest produced by PlannerService."""

    goal: str
    steps: tuple[PlanStep, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionPlan:
        raw_steps = data.get("steps") or []
        steps = tuple(
            PlanStep.from_dict(item) for item in raw_steps if isinstance(item, dict)
        )
        return cls(goal=str(data.get("goal", "")), steps=steps)
