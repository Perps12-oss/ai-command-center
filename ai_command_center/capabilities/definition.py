"""CapabilityDefinition — planner-facing workspace operation contract."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    """Canonical capability metadata. Planners never see handler internals."""

    id: str
    domain: str
    description: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    mutates_world_model: bool = False
    requires_confirmation: bool = False
    requires_human_approval: bool = False
    planner_visible: bool = True
    execution_handler: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_prompt_spec(self) -> dict[str, object]:
        return {
            "name": self.id,
            "capability": self.id,
            "domain": self.domain,
            "description": self.description,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "mutates_world_model": self.mutates_world_model,
            "requires_confirmation": self.requires_confirmation,
            "requires_approval": self.requires_human_approval,
            "risk": "high" if self.requires_human_approval else "low",
            "handler": "",  # never expose implementation to planner
        }
