"""Planner-facing capability metadata — no handlers exposed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CapabilityPromptSpec:
    """Stable action vocabulary entry for the planner layer."""

    name: str
    description: str
    risk: str = "low"
    requires_approval: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "risk": self.risk,
            "requires_approval": self.requires_approval,
            "parameters": dict(self.parameters),
        }
