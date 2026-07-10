"""Plan Evaluation Framework — metrics and decisions for plan assessment.

This module defines the formal evaluation framework that assesses plan quality
across multiple dimensions. Per ACC Planner Constitution Phase C0:
- 05_PLAN_EVALUATION_FRAMEWORK.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvaluationDecision(Enum):
    """Decision outcomes from plan evaluation."""

    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


@dataclass(frozen=True, slots=True)
class MetricComponent:
    """A component of an evaluation metric."""

    score: float
    weight: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "weight": self.weight,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetricComponent:
        return cls(
            score=float(data.get("score", 0.0)),
            weight=float(data.get("weight", 1.0)),
            details=dict(data.get("details") or {}),
        )


@dataclass(frozen=True, slots=True)
class MetricThresholds:
    """Thresholds for metric interpretation."""

    critical: float = 0.0
    acceptable: float = 0.0
    excellent: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "critical": self.critical,
            "acceptable": self.acceptable,
            "excellent": self.excellent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetricThresholds:
        return cls(
            critical=float(data.get("critical", 0.0)),
            acceptable=float(data.get("acceptable", 0.0)),
            excellent=float(data.get("excellent", 0.0)),
        )

    def interpret(self, score: float) -> str:
        """Interpret a score against thresholds."""
        if score >= self.excellent:
            return "excellent"
        elif score >= self.acceptable:
            return "acceptable"
        elif score >= self.critical:
            return "needs_work"
        else:
            return "critical"


@dataclass(frozen=True, slots=True)
class SafetyScore:
    """Measures the safety profile of a plan.

    Components:
    - Destructive Potential: How destructive are the planned actions?
    - Reversibility: Can actions be undone?
    - Approval Requirements: How many approvals are needed?
    """

    score: float  # Overall 0-1
    destructive_potential: MetricComponent = field(default_factory=MetricComponent)
    reversibility: MetricComponent = field(default_factory=MetricComponent)
    approval_requirements: MetricComponent = field(default_factory=MetricComponent)
    thresholds: MetricThresholds = field(default_factory=MetricThresholds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "components": {
                "destructivePotential": self.destructive_potential.to_dict(),
                "reversibility": self.reversibility.to_dict(),
                "approvalRequirements": self.approval_requirements.to_dict(),
            },
            "thresholds": self.thresholds.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SafetyScore:
        components = data.get("components", {})
        return cls(
            score=float(data.get("score", 0.0)),
            destructive_potential=MetricComponent.from_dict(
                components.get("destructivePotential", {})
            ),
            reversibility=MetricComponent.from_dict(components.get("reversibility", {})),
            approval_requirements=MetricComponent.from_dict(
                components.get("approvalRequirements", {})
            ),
            thresholds=MetricThresholds.from_dict(data.get("thresholds", {})),
        )

    @classmethod
    def default(cls) -> SafetyScore:
        """Create a default safety score with reasonable defaults."""
        return cls(
            score=1.0,
            destructive_potential=MetricComponent(score=1.0, weight=0.4),
            reversibility=MetricComponent(score=1.0, weight=0.3),
            approval_requirements=MetricComponent(score=1.0, weight=0.3),
            thresholds=MetricThresholds(critical=0.5, acceptable=0.75, excellent=0.9),
        )


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Breakdown of cost components."""

    time_cost: float = 0.0
    resource_cost: float = 0.0
    risk_cost: float = 0.0
    user_effort_cost: float = 0.0
    estimated_duration: str = ""  # e.g., "5m"
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": {
                "cost": self.time_cost,
                "estimated": self.estimated_duration,
            },
            "resources": self.resource_cost,
            "risk": self.risk_cost,
            "userEffort": self.user_effort_cost,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CostBreakdown:
        time_data = data.get("time", {})
        return cls(
            time_cost=float(time_data.get("cost", 0.0)),
            estimated_duration=str(time_data.get("estimated", "")),
            resource_cost=float(data.get("resources", 0.0)),
            risk_cost=float(data.get("risk", 0.0)),
            user_effort_cost=float(data.get("userEffort", 0.0)),
            confidence=float(data.get("confidence", 1.0)),
        )


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Measures the expected cost of executing a plan."""

    total: float  # Total cost in USD
    currency: str = "USD"
    breakdown: CostBreakdown = field(default_factory=CostBreakdown)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "currency": self.currency,
            "breakdown": self.breakdown.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CostEstimate:
        return cls(
            total=float(data.get("total", 0.0)),
            currency=str(data.get("currency", "USD")),
            breakdown=CostBreakdown.from_dict(data.get("breakdown") or {}),
        )

    @classmethod
    def default(cls) -> CostEstimate:
        """Create a default cost estimate."""
        return cls(
            total=0.0,
            currency="USD",
            breakdown=CostBreakdown(),
        )


@dataclass(frozen=True, slots=True)
class ComplexityScore:
    """Measures the complexity of a plan.

    Components:
    - Action Count: Number of actions
    - Dependency Depth: Maximum dependency depth
    - Branching Factor: Maximum parallel branches
    - Failure Points: Number of potential failure points
    """

    score: float  # Overall 0-1 (lower = simpler)
    action_count: MetricComponent = field(default_factory=MetricComponent)
    dependency_depth: MetricComponent = field(default_factory=MetricComponent)
    branching_factor: MetricComponent = field(default_factory=MetricComponent)
    failure_points: MetricComponent = field(default_factory=MetricComponent)
    thresholds: MetricThresholds = field(default_factory=MetricThresholds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "components": {
                "actionCount": self.action_count.to_dict(),
                "dependencyDepth": self.dependency_depth.to_dict(),
                "branchingFactor": self.branching_factor.to_dict(),
                "failurePoints": self.failure_points.to_dict(),
            },
            "thresholds": self.thresholds.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComplexityScore:
        components = data.get("components", {})
        return cls(
            score=float(data.get("score", 0.0)),
            action_count=MetricComponent.from_dict(components.get("actionCount", {})),
            dependency_depth=MetricComponent.from_dict(components.get("dependencyDepth", {})),
            branching_factor=MetricComponent.from_dict(components.get("branchingFactor", {})),
            failure_points=MetricComponent.from_dict(components.get("failurePoints", {})),
            thresholds=MetricThresholds.from_dict(data.get("thresholds", {})),
        )

    @classmethod
    def default(cls) -> ComplexityScore:
        """Create a default complexity score."""
        return cls(
            score=0.0,
            action_count=MetricComponent(score=0.0, weight=0.25),
            dependency_depth=MetricComponent(score=0.0, weight=0.25),
            branching_factor=MetricComponent(score=0.0, weight=0.25),
            failure_points=MetricComponent(score=0.0, weight=0.25),
            thresholds=MetricThresholds(critical=0.7, acceptable=0.5, excellent=0.3),
        )


@dataclass(frozen=True, slots=True)
class ConfidenceLevel:
    """Measures the planner's confidence in plan success.

    Components:
    - State Certainty: How certain is the world state?
    - Historical Success: Past success rate for similar plans?
    - Planner Certainty: Model's own confidence?
    """

    score: float  # Overall 0-1
    state_certainty: MetricComponent = field(default_factory=MetricComponent)
    historical_success: MetricComponent = field(default_factory=MetricComponent)
    planner_certainty: MetricComponent = field(default_factory=MetricComponent)
    thresholds: MetricThresholds = field(default_factory=MetricThresholds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "components": {
                "stateCertainty": self.state_certainty.to_dict(),
                "historicalSuccess": self.historical_success.to_dict(),
                "plannerCertainty": self.planner_certainty.to_dict(),
            },
            "thresholds": self.thresholds.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfidenceLevel:
        components = data.get("components", {})
        return cls(
            score=float(data.get("score", 0.0)),
            state_certainty=MetricComponent.from_dict(
                components.get("stateCertainty", {})
            ),
            historical_success=MetricComponent.from_dict(
                components.get("historicalSuccess", {})
            ),
            planner_certainty=MetricComponent.from_dict(
                components.get("plannerCertainty", {})
            ),
            thresholds=MetricThresholds.from_dict(data.get("thresholds", {})),
        )

    @classmethod
    def default(cls) -> ConfidenceLevel:
        """Create a default confidence level."""
        return cls(
            score=1.0,
            state_certainty=MetricComponent(score=1.0, weight=0.3),
            historical_success=MetricComponent(score=1.0, weight=0.3),
            planner_certainty=MetricComponent(score=1.0, weight=0.4),
            thresholds=MetricThresholds(critical=0.4, acceptable=0.6, excellent=0.9),
        )


@dataclass(frozen=True, slots=True)
class GoalAlignment:
    """Measures how well the plan achieves the stated goal.

    Components:
    - Direct Contribution: How directly do actions contribute?
    - Expected Outcome Quality: Expected quality of outcome?
    - Scope Completeness: Does plan cover full scope?
    """

    score: float  # Overall 0-1
    direct_contribution: MetricComponent = field(default_factory=MetricComponent)
    expected_outcome_quality: MetricComponent = field(default_factory=MetricComponent)
    scope_completeness: MetricComponent = field(default_factory=MetricComponent)
    thresholds: MetricThresholds = field(default_factory=MetricThresholds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "components": {
                "directContribution": self.direct_contribution.to_dict(),
                "expectedOutcomeQuality": self.expected_outcome_quality.to_dict(),
                "scopeCompleteness": self.scope_completeness.to_dict(),
            },
            "thresholds": self.thresholds.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoalAlignment:
        components = data.get("components", {})
        return cls(
            score=float(data.get("score", 0.0)),
            direct_contribution=MetricComponent.from_dict(
                components.get("directContribution", {})
            ),
            expected_outcome_quality=MetricComponent.from_dict(
                components.get("expectedOutcomeQuality", {})
            ),
            scope_completeness=MetricComponent.from_dict(
                components.get("scopeCompleteness", {})
            ),
            thresholds=MetricThresholds.from_dict(data.get("thresholds", {})),
        )

    @classmethod
    def default(cls) -> GoalAlignment:
        """Create a default goal alignment score."""
        return cls(
            score=1.0,
            direct_contribution=MetricComponent(score=1.0, weight=0.5),
            expected_outcome_quality=MetricComponent(score=1.0, weight=0.3),
            scope_completeness=MetricComponent(score=1.0, weight=0.2),
            thresholds=MetricThresholds(critical=0.6, acceptable=0.75, excellent=0.9),
        )


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Complete set of evaluation metrics for a plan."""

    safety_score: SafetyScore = field(default_factory=SafetyScore.default)
    cost_estimate: CostEstimate = field(default_factory=CostEstimate.default)
    complexity_score: ComplexityScore = field(default_factory=ComplexityScore.default)
    confidence_level: ConfidenceLevel = field(default_factory=ConfidenceLevel.default)
    goal_alignment: GoalAlignment = field(default_factory=GoalAlignment.default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "safetyScore": self.safety_score.to_dict(),
            "costEstimate": self.cost_estimate.to_dict(),
            "complexityScore": self.complexity_score.to_dict(),
            "confidenceLevel": self.confidence_level.to_dict(),
            "goalAlignment": self.goal_alignment.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationMetrics:
        return cls(
            safety_score=SafetyScore.from_dict(data.get("safetyScore", {})),
            cost_estimate=CostEstimate.from_dict(data.get("costEstimate", {})),
            complexity_score=ComplexityScore.from_dict(data.get("complexityScore", {})),
            confidence_level=ConfidenceLevel.from_dict(data.get("confidenceLevel", {})),
            goal_alignment=GoalAlignment.from_dict(data.get("goalAlignment", {})),
        )


@dataclass(frozen=True, slots=True)
class EvaluationFailure:
    """A failed evaluation criterion."""

    criterion: str = ""
    expected: str = ""
    actual: str = ""
    severity: str = "critical"  # critical, warning
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion": self.criterion,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationFailure:
        return cls(
            criterion=str(data.get("criterion", "")),
            expected=str(data.get("expected", "")),
            actual=str(data.get("actual", "")),
            severity=str(data.get("severity", "critical")),
            message=str(data.get("message", "")),
        )


@dataclass(frozen=True, slots=True)
class EvaluationImprovement:
    """Suggested improvement for a plan."""

    improvement_type: str = ""  # reduce_complexity, increase_safety, etc.
    current: float = 0.0
    target: float = 0.0
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.improvement_type,
            "current": self.current,
            "target": self.target,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationImprovement:
        return cls(
            improvement_type=str(data.get("type", "")),
            current=float(data.get("current", 0.0)),
            target=float(data.get("target", 0.0)),
            suggestion=str(data.get("suggestion", "")),
        )


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Complete result of plan evaluation."""

    decision: EvaluationDecision
    reason: str = ""
    metrics: EvaluationMetrics = field(default_factory=EvaluationMetrics)
    overall_score: float = 0.0
    failures: tuple[EvaluationFailure, ...] = field(default_factory=tuple)
    improvements: tuple[EvaluationImprovement, ...] = field(default_factory=tuple)
    approval_level: str = "standard"  # standard, conditional

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "metrics": self.metrics.to_dict(),
            "overallScore": self.overall_score,
            "failures": [f.to_dict() for f in self.failures],
            "improvements": [i.to_dict() for i in self.improvements],
            "approvalLevel": self.approval_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationResult:
        try:
            decision = EvaluationDecision(data.get("decision", "approve"))
        except ValueError:
            decision = EvaluationDecision.APPROVE

        return cls(
            decision=decision,
            reason=str(data.get("reason", "")),
            metrics=EvaluationMetrics.from_dict(data.get("metrics") or {}),
            overall_score=float(data.get("overallScore", 0.0)),
            failures=tuple(
                EvaluationFailure.from_dict(f) for f in data.get("failures") or []
            ),
            improvements=tuple(
                EvaluationImprovement.from_dict(i) for i in data.get("improvements") or []
            ),
            approval_level=str(data.get("approvalLevel", "standard")),
        )

    @property
    def is_approved(self) -> bool:
        """Check if the plan is approved."""
        return self.decision == EvaluationDecision.APPROVE

    @property
    def is_rejected(self) -> bool:
        """Check if the plan is rejected."""
        return self.decision == EvaluationDecision.REJECT

    @property
    def needs_revision(self) -> bool:
        """Check if the plan needs revision."""
        return self.decision == EvaluationDecision.REVISE


@dataclass(frozen=True, slots=True)
class EvaluationWeights:
    """Weights for computing overall evaluation score."""

    safety: float = 0.30
    cost: float = 0.15
    complexity: float = 0.15
    confidence: float = 0.20
    goal_alignment: float = 0.20

    def to_dict(self) -> dict[str, Any]:
        return {
            "safety": self.safety,
            "cost": self.cost,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "goalAlignment": self.goal_alignment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationWeights:
        return cls(
            safety=float(data.get("safety", 0.30)),
            cost=float(data.get("cost", 0.15)),
            complexity=float(data.get("complexity", 0.15)),
            confidence=float(data.get("confidence", 0.20)),
            goal_alignment=float(data.get("goalAlignment", 0.20)),
        )

    @classmethod
    def default(cls) -> EvaluationWeights:
        """Create default weights as per spec."""
        return cls()


# Default evaluation thresholds
DEFAULT_EVALUATION_THRESHOLDS = {
    "safety_score": {
        "min_approve": 0.75,
        "min_revise": 0.5,
        "max_reject": 0.5,
    },
    "cost_estimate": {
        "max_approve": 100.0,
        "max_revise": 250.0,
    },
    "complexity_score": {
        "max_approve": 0.6,  # Lower is better (normalized)
        "max_revise": 0.8,
    },
    "confidence_level": {
        "min_approve": 0.7,
        "min_revise": 0.4,
    },
    "goal_alignment": {
        "min_approve": 0.8,
        "min_revise": 0.6,
    },
    "overall_score": {
        "min_approve": 0.75,
        "min_revise": 0.5,
    },
}
