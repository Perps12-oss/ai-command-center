"""Model Routing — AI model selection for planning tasks.

This module defines the model routing system that selects the appropriate
AI model for different planning tasks.
Per ACC Planner Constitution Phase C0:
- 09_MODEL_ROUTING_SPEC.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelType(Enum):
    """Type of planning model."""

    FAST = "fast"  # Simple goals, fast decisions
    DEEP = "deep"  # Complex reasoning
    EVALUATOR = "evaluator"  # Independent critique


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """Capabilities of a model."""

    capabilities: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": list(self.capabilities),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelCapabilities:
        return cls(
            capabilities=tuple(str(c) for c in data.get("capabilities") or []),
            limitations=tuple(str(l) for l in data.get("limitations") or []),
        )


@dataclass(frozen=True, slots=True)
class ModelPerformance:
    """Performance characteristics of a model."""

    avg_latency_ms: int = 0
    p50_latency_ms: int = 0
    p95_latency_ms: int = 0
    p99_latency_ms: int = 0
    cost_per_1k_tokens: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "avgLatencyMs": self.avg_latency_ms,
            "p50LatencyMs": self.p50_latency_ms,
            "p95LatencyMs": self.p95_latency_ms,
            "p99LatencyMs": self.p99_latency_ms,
            "costPer1kTokens": self.cost_per_1k_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelPerformance:
        return cls(
            avg_latency_ms=int(data.get("avgLatencyMs", 0)),
            p50_latency_ms=int(data.get("p50LatencyMs", 0)),
            p95_latency_ms=int(data.get("p95LatencyMs", 0)),
            p99_latency_ms=int(data.get("p99LatencyMs", 0)),
            cost_per_1k_tokens=float(data.get("costPer1kTokens", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class ModelUseCase:
    """A valid use case for a model."""

    use_case: str = ""
    example: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "useCase": self.use_case,
            "example": self.example,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelUseCase:
        return cls(
            use_case=str(data.get("useCase", "")),
            example=str(data.get("example", "")),
        )


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Configuration for a planning model."""

    model_id: str
    name: str
    model_type: ModelType
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    performance: ModelPerformance = field(default_factory=ModelPerformance)
    use_cases: tuple[ModelUseCase, ...] = field(default_factory=tuple)
    max_tokens: int = 8000
    available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "modelId": self.model_id,
            "name": self.name,
            "type": self.model_type.value,
            "capabilities": self.capabilities.to_dict(),
            "performance": self.performance.to_dict(),
            "useCases": [u.to_dict() for u in self.use_cases],
            "maxTokens": self.max_tokens,
            "available": self.available,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        try:
            model_type = ModelType(data.get("type", ModelType.FAST.value))
        except ValueError:
            model_type = ModelType.FAST

        return cls(
            model_id=str(data["modelId"]),
            name=str(data["name"]),
            model_type=model_type,
            capabilities=ModelCapabilities.from_dict(data.get("capabilities") or {}),
            performance=ModelPerformance.from_dict(data.get("performance") or {}),
            use_cases=tuple(
                ModelUseCase.from_dict(u) for u in data.get("useCases") or []
            ),
            max_tokens=int(data.get("maxTokens", 8000)),
            available=bool(data.get("available", True)),
        )


# Default model configurations
DEFAULT_MODELS = {
    "fast_planner": ModelConfig(
        model_id="fast_planner",
        name="Qwen 2.5",
        model_type=ModelType.FAST,
        capabilities=ModelCapabilities(
            capabilities=("simple_planning", "pattern_matching", "quick_responses"),
            limitations=("complex_reasoning", "multi_step_planning", "deep_analysis"),
        ),
        performance=ModelPerformance(
            avg_latency_ms=500,
            p50_latency_ms=400,
            p95_latency_ms=1000,
            p99_latency_ms=2000,
            cost_per_1k_tokens=0.001,
        ),
        use_cases=(
            ModelUseCase(
                use_case="single_action_goals",
                example='"Create a new file"',
            ),
            ModelUseCase(
                use_case="pattern_based_planning",
                example='"Add a todo item"',
            ),
            ModelUseCase(
                use_case="routine_tasks",
                example='"Search for files"',
            ),
        ),
        max_tokens=2000,
    ),
    "deep_planner": ModelConfig(
        model_id="deep_planner",
        name="Claude 3.5 Sonnet",
        model_type=ModelType.DEEP,
        capabilities=ModelCapabilities(
            capabilities=(
                "complex_reasoning",
                "multi_step_planning",
                "goal_decomposition",
                "constraint_reasoning",
                "risk_assessment",
            ),
            limitations=("latency", "cost"),
        ),
        performance=ModelPerformance(
            avg_latency_ms=3000,
            p50_latency_ms=2500,
            p95_latency_ms=8000,
            p99_latency_ms=15000,
            cost_per_1k_tokens=0.015,
        ),
        use_cases=(
            ModelUseCase(
                use_case="complex_deployment_plans",
                example='"Deploy with blue-green strategy"',
            ),
            ModelUseCase(
                use_case="multi_objective_optimization",
                example='"Optimize for cost and speed"',
            ),
            ModelUseCase(
                use_case="novel_situations",
                example='"Handle unknown error scenario"',
            ),
        ),
        max_tokens=8000,
    ),
    "evaluator": ModelConfig(
        model_id="evaluator",
        name="Claude 3.5 Sonnet",
        model_type=ModelType.EVALUATOR,
        capabilities=ModelCapabilities(
            capabilities=(
                "critical_analysis",
                "risk_assessment",
                "validation",
                "quality_assessment",
            ),
            limitations=("planning", "generation"),
        ),
        performance=ModelPerformance(
            avg_latency_ms=2000,
            p50_latency_ms=1500,
            p95_latency_ms=5000,
            p99_latency_ms=10000,
            cost_per_1k_tokens=0.015,
        ),
        use_cases=(
            ModelUseCase(
                use_case="plan_evaluation",
                example="Validate plan safety and correctness",
            ),
            ModelUseCase(
                use_case="safety_assessment",
                example="Identify potential risks",
            ),
            ModelUseCase(
                use_case="constraint_validation",
                example="Verify constraint compliance",
            ),
        ),
        max_tokens=4000,
    ),
}


@dataclass(frozen=True, slots=True)
class RoutingContext:
    """Context for routing decision."""

    goal_type: str = ""  # single_action, multi_step, complex, novel
    complexity: float = 0.0  # 0-1
    risk_level: str = "low"  # low, medium, high, critical
    confidence_expected: float = 1.0
    retry_count: int = 0
    budget_remaining: float = 10.0  # USD
    available_models: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goalType": self.goal_type,
            "complexity": self.complexity,
            "riskLevel": self.risk_level,
            "confidenceExpected": self.confidence_expected,
            "retryCount": self.retry_count,
            "budgetRemaining": self.budget_remaining,
            "availableModels": list(self.available_models),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoutingContext:
        return cls(
            goal_type=str(data.get("goalType", "")),
            complexity=float(data.get("complexity", 0.0)),
            risk_level=str(data.get("riskLevel", "low")),
            confidence_expected=float(data.get("confidenceExpected", 1.0)),
            retry_count=int(data.get("retryCount", 0)),
            budget_remaining=float(data.get("budgetRemaining", 10.0)),
            available_models=tuple(str(m) for m in data.get("availableModels") or []),
        )


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Result of routing decision."""

    model_id: str
    rationale: str = ""
    fallback_model_id: str = ""
    estimated_latency_ms: int = 0
    estimated_cost: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    evaluator_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "modelId": self.model_id,
            "rationale": self.rationale,
            "fallbackModelId": self.fallback_model_id,
            "estimatedLatencyMs": self.estimated_latency_ms,
            "estimatedCost": self.estimated_cost,
            "warnings": list(self.warnings),
            "evaluatorRequired": self.evaluator_required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoutingDecision:
        return cls(
            model_id=str(data["modelId"]),
            rationale=str(data.get("rationale", "")),
            fallback_model_id=str(data.get("fallbackModelId", "")),
            estimated_latency_ms=int(data.get("estimatedLatencyMs", 0)),
            estimated_cost=float(data.get("estimatedCost", 0.0)),
            warnings=tuple(str(w) for w in data.get("warnings") or []),
            evaluator_required=bool(data.get("evaluatorRequired", False)),
        )


@dataclass(frozen=True, slots=True)
class EscalationDecision:
    """Decision to escalate to human reviewer."""

    reason: str = ""  # low_confidence, repeated_failure, high_complexity
    target: str = "human_reviewer"
    urgency: str = "normal"  # low, normal, high
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "target": self.target,
            "urgency": self.urgency,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EscalationDecision:
        return cls(
            reason=str(data.get("reason", "")),
            target=str(data.get("target", "human_reviewer")),
            urgency=str(data.get("urgency", "normal")),
            details=dict(data.get("details") or {}),
        )


@dataclass(frozen=True, slots=True)
class FallbackDecision:
    """Decision when primary model fails."""

    new_model_id: str = ""
    preserve_context: bool = True
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "newModelId": self.new_model_id,
            "preserveContext": self.preserve_context,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FallbackDecision:
        return cls(
            new_model_id=str(data.get("newModelId", "")),
            preserve_context=bool(data.get("preserveContext", True)),
            warnings=tuple(str(w) for w in data.get("warnings") or []),
        )


@dataclass(frozen=True, slots=True)
class CostControls:
    """Cost control configuration."""

    session_budget: float = 10.0  # USD
    reset_period: str = "daily"
    fast_model_cost_limit: float = 0.05
    deep_model_cost_limit: float = 0.50
    evaluator_cost_limit: float = 0.25
    prefer_cheaper: bool = True
    cheap_threshold: float = 0.8  # Use cheap model when confidence > this

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessionBudget": self.session_budget,
            "resetPeriod": self.reset_period,
            "fastModelCostLimit": self.fast_model_cost_limit,
            "deepModelCostLimit": self.deep_model_cost_limit,
            "evaluatorCostLimit": self.evaluator_cost_limit,
            "preferCheaper": self.prefer_cheaper,
            "cheapThreshold": self.cheap_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CostControls:
        return cls(
            session_budget=float(data.get("sessionBudget", 10.0)),
            reset_period=str(data.get("resetPeriod", "daily")),
            fast_model_cost_limit=float(data.get("fastModelCostLimit", 0.05)),
            deep_model_cost_limit=float(data.get("deepModelCostLimit", 0.50)),
            evaluator_cost_limit=float(data.get("evaluatorCostLimit", 0.25)),
            prefer_cheaper=bool(data.get("preferCheaper", True)),
            cheap_threshold=float(data.get("cheapThreshold", 0.8)),
        )


# Escalation thresholds from spec
ESCALATION_THRESHOLDS = {
    "confidence_threshold": 0.4,
    "complexity_threshold": 0.8,
    "failure_threshold": 3,
    "cost_threshold": 10.0,
}

# Latency targets from spec (ms)
LATENCY_TARGETS = {
    "fast_model": {
        "avg": 500,
        "p50": 400,
        "p95": 1000,
        "p99": 2000,
    },
    "deep_model": {
        "avg": 3000,
        "p50": 2500,
        "p95": 8000,
        "p99": 15000,
    },
    "evaluator": {
        "avg": 2000,
        "p50": 1500,
        "p95": 5000,
        "p99": 10000,
    },
}
