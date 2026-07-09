"""External capability manifest — MCP/email/calendar via ARI (Invariant 13)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ExternalCapabilityManifest:
    """Declarative external capability exposed to the planner catalog."""

    capability_id: str
    name: str
    description: str
    provider_id: str
    risk: str = "medium"
    kind: str = "mcp"
    parameters: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "provider_id": self.provider_id,
            "risk": self.risk,
            "kind": self.kind,
            "parameters": dict(self.parameters),
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExternalCapabilityManifest:
        return cls(
            capability_id=str(data.get("capability_id", "")),
            name=str(data.get("name", data.get("capability_id", ""))),
            description=str(data.get("description", "")),
            provider_id=str(data.get("provider_id", "mcp")),
            risk=str(data.get("risk", "medium")),
            kind=str(data.get("kind", "mcp")),
            parameters=dict(data.get("parameters") or {}),
            enabled=bool(data.get("enabled", True)),
        )

    def to_prompt_spec(self) -> dict[str, Any]:
        """Planner-facing spec shape (no handlers)."""
        requires = self.risk.lower() in {"medium", "high"}
        return {
            "name": self.capability_id,
            "description": self.description or self.name,
            "risk": self.risk,
            "requires_approval": requires,
            "parameters": dict(self.parameters),
            "source": "external",
            "provider_id": self.provider_id,
            "kind": self.kind,
        }
