"""State Authority contract domain types (R1 Priority 3 / Stage 2).

``StateContext`` remains the v1 projection DTO carried on the bus and into
the planner. ``StateProjection`` is an alias for that DTO so the contract
surface (query → StateProjection) can evolve without breaking callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ai_command_center.domain.state_context import StateContext

# Contract v1: projection DTO is StateContext.
StateProjection = StateContext


@dataclass(frozen=True, slots=True)
class StateQuery:
    """Structured read of authoritative workspace reality. No side effects."""

    workspace_id: str = ""
    text: str = ""
    entity_types: tuple[str, ...] = ()
    include_memories: bool = True
    include_goals: bool = True
    # Sync intake path: skip cold recover + heavy lookups (Perf Art IV).
    light: bool = False


@dataclass(frozen=True, slots=True)
class ProjectionScope:
    """Scope for decision / UI-facing projection builds."""

    workspace_id: str = ""
    text: str = ""


@dataclass(frozen=True, slots=True)
class StateDelta:
    """Authoritative state change request (mutate path — Stage 2+).

    ``operations`` are opaque dicts for now; Slice 1 does not unify mutation
    backends. Callers must not invent durable truth outside State Authority.
    """

    workspace_id: str = ""
    operations: tuple[dict[str, Any], ...] = ()
    correlation_id: str = ""
    reason: str = ""


@dataclass(frozen=True, slots=True)
class MutationReceipt:
    """Receipt for an authoritative mutation (correlatable with execution)."""

    receipt_id: str = field(default_factory=lambda: uuid4().hex)
    workspace_id: str = ""
    ok: bool = False
    message: str = ""
    correlation_id: str = ""
    applied: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "workspace_id": self.workspace_id,
            "ok": self.ok,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "applied": list(self.applied),
        }


__all__ = [
    "MutationReceipt",
    "ProjectionScope",
    "StateDelta",
    "StateProjection",
    "StateQuery",
]
