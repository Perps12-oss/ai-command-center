"""Constraint Engine — definitions for planning constraints.

This module defines the constraint system that governs what the Planner
can and cannot propose. Per ACC Planner Constitution Phase C0:
- 04_CONSTRAINT_ENGINE_SPEC.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConstraintType(Enum):
    """Constraint type classification."""

    HARD = "hard"  # Must be satisfied, violation = rejection
    SOFT = "soft"  # Should be satisfied, violation = penalty
    USER = "user"  # User preferences
    SYSTEM = "system"  # System limits
    SAFETY = "safety"  # Safety requirements
    POLICY = "policy"  # Organizational policies


class ConstraintCategory(Enum):
    """Constraint category classification."""

    SAFETY = "safety"
    CRITICAL = "critical"
    POLICY = "policy"
    RESOURCE = "resource"
    PREFERENCE = "preference"
    COMPLIANCE = "compliance"


class EnforcementMode(Enum):
    """How strictly a constraint is enforced."""

    STRICT = "strict"  # Cannot be violated
    WEIGHTED = "weighted"  # Contributes to score
    ADVISORY = "advisory"  # Warning only


class ConstraintExpressionType(Enum):
    """Types of constraint expressions."""

    FORBIDDEN = "forbidden"
    REQUIRED = "required"
    PREFERENCE = "preference"
    LIMIT = "limit"
    SCOPE = "scope"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_LOGGING = "require_logging"


@dataclass(frozen=True, slots=True)
class ConstraintCondition:
    """A condition for a constraint expression."""

    condition_type: str = ""  # e.g., "automatic_trigger", "trigger", etc.
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.condition_type,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstraintCondition:
        return cls(
            condition_type=str(data.get("type", "")),
            value=data.get("value"),
        )


@dataclass(frozen=True, slots=True)
class ConstraintExpression:
    """The core expression of a constraint."""

    expression_type: ConstraintExpressionType
    actions: tuple[str, ...] = field(default_factory=tuple)  # e.g., "file.*", "delete"
    conditions: tuple[ConstraintCondition, ...] = field(default_factory=tuple)
    parameters: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0  # For soft constraints
    scoring: dict[str, float] = field(default_factory=dict)  # e.g., {"reversible": 1.0}
    allowed_scopes: tuple[str, ...] = field(default_factory=tuple)
    blocked_scopes: tuple[str, ...] = field(default_factory=tuple)
    max_value: float = 0.0  # For LIMIT type

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.expression_type.value,
            "actions": list(self.actions),
            "conditions": [c.to_dict() for c in self.conditions],
            "parameters": dict(self.parameters),
            "weight": self.weight,
            "scoring": dict(self.scoring),
            "allowedScopes": list(self.allowed_scopes),
            "blockedScopes": list(self.blocked_scopes),
            "max": self.max_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstraintExpression:
        expr_type = data.get("type", "forbidden")
        try:
            expression_type = ConstraintExpressionType(expr_type)
        except ValueError:
            expression_type = ConstraintExpressionType.FORBIDDEN

        return cls(
            expression_type=expression_type,
            actions=tuple(str(a) for a in data.get("actions") or []),
            conditions=tuple(
                ConstraintCondition.from_dict(c) for c in data.get("conditions") or []
            ),
            parameters=dict(data.get("parameters") or {}),
            weight=float(data.get("weight", 1.0)),
            scoring=dict(data.get("scoring") or {}),
            allowed_scopes=tuple(str(s) for s in data.get("allowedScopes") or []),
            blocked_scopes=tuple(str(s) for s in data.get("blockedScopes") or []),
            max_value=float(data.get("max", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class Constraint:
    """A planning constraint.

    Constraints define the boundaries within which planning occurs.
    """

    constraint_id: str
    constraint_type: ConstraintType
    category: ConstraintCategory
    name: str
    description: str = ""
    expression: ConstraintExpression = field(default_factory=ConstraintExpression)
    enforcement: EnforcementMode = EnforcementMode.STRICT
    overrideable: bool = False
    source: str = ""  # e.g., "system", "user_preference", "policy"
    confidence: float = 1.0  # How certain we are about this constraint
    priority: int = 0  # Higher = more important

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraintId": self.constraint_id,
            "type": self.constraint_type.value,
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "expression": self.expression.to_dict(),
            "enforcement": self.enforcement.value,
            "overrideable": self.overrideable,
            "source": self.source,
            "confidence": self.confidence,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Constraint:
        try:
            constraint_type = ConstraintType(data.get("type", "hard"))
        except ValueError:
            constraint_type = ConstraintType.HARD

        try:
            category = ConstraintCategory(data.get("category", "safety"))
        except ValueError:
            category = ConstraintCategory.SAFETY

        try:
            enforcement = EnforcementMode(data.get("enforcement", "strict"))
        except ValueError:
            enforcement = EnforcementMode.STRICT

        return cls(
            constraint_id=str(data["constraintId"]),
            constraint_type=constraint_type,
            category=category,
            name=str(data["name"]),
            description=str(data.get("description", "")),
            expression=ConstraintExpression.from_dict(data.get("expression") or {}),
            enforcement=enforcement,
            overrideable=bool(data.get("overrideable", False)),
            source=str(data.get("source", "")),
            confidence=float(data.get("confidence", 1.0)),
            priority=int(data.get("priority", 0)),
        )

    def is_hard(self) -> bool:
        """Check if this is a hard constraint."""
        return self.constraint_type == ConstraintType.HARD

    def is_safety(self) -> bool:
        """Check if this is a safety constraint."""
        return self.constraint_type == ConstraintType.SAFETY

    def can_override(self) -> bool:
        """Check if this constraint can be overridden."""
        return self.overrideable and not self.is_safety()


@dataclass(frozen=True, slots=True)
class ConstraintViolation:
    """A violation of a constraint by a planned action."""

    constraint_id: str
    constraint_name: str
    violated_node_id: str = ""  # The node that violated the constraint
    severity: str = "error"  # error, warning
    message: str = ""
    can_override: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraintId": self.constraint_id,
            "constraintName": self.constraint_name,
            "violatedNodeId": self.violated_node_id,
            "severity": self.severity,
            "message": self.message,
            "canOverride": self.can_override,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstraintViolation:
        return cls(
            constraint_id=str(data["constraintId"]),
            constraint_name=str(data["constraintName"]),
            violated_node_id=str(data.get("violatedNodeId", "")),
            severity=str(data.get("severity", "error")),
            message=str(data.get("message", "")),
            can_override=bool(data.get("canOverride", False)),
        )


@dataclass(frozen=True, slots=True)
class ConstraintSet:
    """A collection of constraints for evaluation."""

    constraints: tuple[Constraint, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraints": [c.to_dict() for c in self.constraints],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstraintSet:
        return cls(
            constraints=tuple(
                Constraint.from_dict(c) for c in data.get("constraints") or []
            ),
        )

    def get_hard_constraints(self) -> tuple[Constraint, ...]:
        """Get all hard constraints."""
        return tuple(c for c in self.constraints if c.is_hard())

    def get_safety_constraints(self) -> tuple[Constraint, ...]:
        """Get all safety constraints."""
        return tuple(c for c in self.constraints if c.is_safety())

    def get_user_constraints(self) -> tuple[Constraint, ...]:
        """Get all user preference constraints."""
        return tuple(c for c in self.constraints if c.constraint_type == ConstraintType.USER)

    def get_soft_constraints(self) -> tuple[Constraint, ...]:
        """Get all soft constraints."""
        return tuple(c for c in self.constraints if c.constraint_type == ConstraintType.SOFT)


@dataclass(frozen=True, slots=True)
class ConstraintEvaluationResult:
    """Result of evaluating constraints against a plan."""

    satisfied: tuple[str, ...] = field(default_factory=tuple)  # constraint IDs
    violated: tuple[ConstraintViolation, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    overall_valid: bool = True
    hard_satisfied: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "satisfied": list(self.satisfied),
            "violated": [v.to_dict() for v in self.violated],
            "warnings": list(self.warnings),
            "overallValid": self.overall_valid,
            "hardSatisfied": self.hard_satisfied,
        }

    @property
    def has_violations(self) -> bool:
        """Check if there are any violations."""
        return len(self.violated) > 0

    @property
    def hard_violations(self) -> tuple[ConstraintViolation, ...]:
        """Get only hard constraint violations."""
        return tuple(v for v in self.violated if v.severity == "error")

    @property
    def warning_violations(self) -> tuple[ConstraintViolation, ...]:
        """Get only warning-level violations."""
        return tuple(v for v in self.violated if v.severity == "warning")


# Default constraints that should always be present
DEFAULT_CONSTRAINTS = ConstraintSet(
    constraints=(
        Constraint(
            constraint_id="no_auto_delete",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.SAFETY,
            name="NoAutomaticFileDeletion",
            description="Files may not be deleted automatically without explicit user approval",
            expression=ConstraintExpression(
                expression_type=ConstraintExpressionType.FORBIDDEN,
                actions=("file.delete",),
                conditions=(ConstraintCondition(condition_type="trigger", value="automatic"),),
            ),
            enforcement=EnforcementMode.STRICT,
            overrideable=False,
            source="system",
            priority=100,
        ),
        Constraint(
            constraint_id="no_auto_spending",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.SAFETY,
            name="NoAutomaticSpending",
            description="No financial transactions without explicit user approval",
            expression=ConstraintExpression(
                expression_type=ConstraintExpressionType.FORBIDDEN,
                actions=("payment.execute",),
                conditions=(ConstraintCondition(condition_type="trigger", value="automatic"),),
            ),
            enforcement=EnforcementMode.STRICT,
            overrideable=False,
            source="system",
            priority=100,
        ),
        Constraint(
            constraint_id="approval_required_destructive",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.SAFETY,
            name="ApprovalRequiredForDestructive",
            description="Destructive operations require explicit human approval",
            expression=ConstraintExpression(
                expression_type=ConstraintExpressionType.REQUIRE_APPROVAL,
                actions=("file.delete", "data.delete", "system.modify"),
            ),
            enforcement=EnforcementMode.STRICT,
            overrideable=False,
            source="system",
            priority=90,
        ),
        Constraint(
            constraint_id="prefer_reversible",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.PREFERENCE,
            name="PreferReversibleActions",
            description="Prefer reversible actions over irreversible ones",
            expression=ConstraintExpression(
                expression_type=ConstraintExpressionType.PREFERENCE,
                actions=("any",),
                weight=0.3,
                scoring={
                    "reversible": 1.0,
                    "partially_reversible": 0.5,
                    "irreversible": 0.0,
                },
            ),
            enforcement=EnforcementMode.WEIGHTED,
            overrideable=True,
            source="system",
            priority=10,
        ),
    )
)
