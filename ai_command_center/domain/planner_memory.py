"""Planner Memory — long-term learning and experience storage.

This module defines the long-term memory system that enables the planner
to improve through experience without retraining foundation models.
Per ACC Planner Constitution Phase C0:
- 08_PLANNER_MEMORY_SPEC.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class GraphStructure:
    """Structure of a plan graph for pattern matching."""

    node_count: int = 0
    depth: int = 0
    branching_factor: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodeCount": self.node_count,
            "depth": self.depth,
            "branchingFactor": self.branching_factor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphStructure:
        return cls(
            node_count=int(data.get("nodeCount", 0)),
            depth=int(data.get("depth", 0)),
            branching_factor=float(data.get("branchingFactor", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    """Snapshot of context for pattern matching."""

    workspace_type: str = ""
    has_tests: bool = False
    has_ci: bool = False
    project_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspaceType": self.workspace_type,
            "hasTests": self.has_tests,
            "hasCI": self.has_ci,
            "projectType": self.project_type,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextSnapshot:
        return cls(
            workspace_type=str(data.get("workspaceType", "")),
            has_tests=bool(data.get("hasTests", False)),
            has_ci=bool(data.get("hasCI", False)),
            project_type=str(data.get("projectType", "")),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class SuccessfulPlanPattern:
    """A successful plan pattern for reuse."""

    pattern_id: str
    plan_type: str = ""  # deployment, configuration, maintenance
    goal_pattern: str = ""  # e.g., "Deploy * to * when *"
    graph_structure: GraphStructure = field(default_factory=GraphStructure)
    context_snapshot: ContextSnapshot = field(default_factory=ContextSnapshot)
    success_rate: float = 1.0
    usage_count: int = 1
    last_used: str = ""  # ISO8601
    created_at: str = ""  # ISO8601
    effectiveness: float = 0.0  # 0-1

    def to_dict(self) -> dict[str, Any]:
        return {
            "patternId": self.pattern_id,
            "planType": self.plan_type,
            "goalPattern": self.goal_pattern,
            "graphStructure": self.graph_structure.to_dict(),
            "contextSnapshot": self.context_snapshot.to_dict(),
            "successRate": self.success_rate,
            "usageCount": self.usage_count,
            "lastUsed": self.last_used,
            "createdAt": self.created_at,
            "effectiveness": self.effectiveness,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SuccessfulPlanPattern:
        return cls(
            pattern_id=str(data["patternId"]),
            plan_type=str(data.get("planType", "")),
            goal_pattern=str(data.get("goalPattern", "")),
            graph_structure=GraphStructure.from_dict(data.get("graphStructure") or {}),
            context_snapshot=ContextSnapshot.from_dict(data.get("contextSnapshot") or {}),
            success_rate=float(data.get("successRate", 1.0)),
            usage_count=int(data.get("usageCount", 1)),
            last_used=str(data.get("lastUsed", "")),
            created_at=str(data.get("createdAt", "")),
            effectiveness=float(data.get("effectiveness", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class FailedPlanPattern:
    """A failed plan pattern to avoid."""

    pattern_id: str
    plan_type: str = ""
    goal_pattern: str = ""
    failure_mode: str = ""
    root_causes: tuple[str, ...] = field(default_factory=tuple)
    graph_structure: GraphStructure = field(default_factory=GraphStructure)
    failure_count: int = 1
    last_failed: str = ""  # ISO8601
    lessons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patternId": self.pattern_id,
            "planType": self.plan_type,
            "goalPattern": self.goal_pattern,
            "failureMode": self.failure_mode,
            "rootCauses": list(self.root_causes),
            "graphStructure": self.graph_structure.to_dict(),
            "failureCount": self.failure_count,
            "lastFailed": self.last_failed,
            "lessons": list(self.lessons),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailedPlanPattern:
        return cls(
            pattern_id=str(data["patternId"]),
            plan_type=str(data.get("planType", "")),
            goal_pattern=str(data.get("goalPattern", "")),
            failure_mode=str(data.get("failureMode", "")),
            root_causes=tuple(str(r) for r in data.get("rootCauses") or []),
            graph_structure=GraphStructure.from_dict(data.get("graphStructure") or {}),
            failure_count=int(data.get("failureCount", 1)),
            last_failed=str(data.get("lastFailed", "")),
            lessons=tuple(str(l) for l in data.get("lessons") or []),
        )


@dataclass(frozen=True, slots=True)
class GoalOutcome:
    """Record of a goal outcome for historical analysis."""

    outcome_id: str
    goal_id: str
    goal_description: str = ""
    outcome: str = ""  # success, partial, failure
    duration: str = ""  # e.g., "5m"
    cost: float = 0.0
    retries: int = 0
    context_snapshot: ContextSnapshot = field(default_factory=ContextSnapshot)
    plan_id: str = ""
    completed_at: str = ""  # ISO8601
    reflection_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcomeId": self.outcome_id,
            "goalId": self.goal_id,
            "goalDescription": self.goal_description,
            "outcome": self.outcome,
            "duration": self.duration,
            "cost": self.cost,
            "retries": self.retries,
            "contextSnapshot": self.context_snapshot.to_dict(),
            "planId": self.plan_id,
            "completedAt": self.completed_at,
            "reflectionId": self.reflection_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoalOutcome:
        return cls(
            outcome_id=str(data["outcomeId"]),
            goal_id=str(data["goalId"]),
            goal_description=str(data.get("goalDescription", "")),
            outcome=str(data.get("outcome", "")),
            duration=str(data.get("duration", "")),
            cost=float(data.get("cost", 0.0)),
            retries=int(data.get("retries", 0)),
            context_snapshot=ContextSnapshot.from_dict(data.get("contextSnapshot") or {}),
            plan_id=str(data.get("planId", "")),
            completed_at=str(data.get("completedAt", "")),
            reflection_id=str(data.get("reflectionId", "")),
        )


@dataclass(frozen=True, slots=True)
class PlannerAdjustment:
    """An adjustment to planner behavior based on reflection."""

    adjustment_type: str = ""  # precondition, constraint, strategy
    description: str = ""
    confidence: float = 1.0
    applicability: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.adjustment_type,
            "description": self.description,
            "confidence": self.confidence,
            "applicability": list(self.applicability),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlannerAdjustment:
        return cls(
            adjustment_type=str(data.get("type", "")),
            description=str(data.get("description", "")),
            confidence=float(data.get("confidence", 1.0)),
            applicability=tuple(str(a) for a in data.get("applicability") or []),
        )


@dataclass(frozen=True, slots=True)
class ReflectionResult:
    """Result of reflection for memory storage."""

    result_id: str
    reflection_id: str = ""
    outcome_id: str = ""
    root_cause_category: str = ""
    root_cause_confidence: float = 1.0
    insights: tuple[str, ...] = field(default_factory=tuple)
    planner_adjustments: tuple[PlannerAdjustment, ...] = field(default_factory=tuple)
    stored_at: str = ""  # ISO8601

    def to_dict(self) -> dict[str, Any]:
        return {
            "resultId": self.result_id,
            "reflectionId": self.reflection_id,
            "outcomeId": self.outcome_id,
            "rootCause": {
                "category": self.root_cause_category,
                "confidence": self.root_cause_confidence,
            },
            "insights": list(self.insights),
            "plannerAdjustments": [a.to_dict() for a in self.planner_adjustments],
            "storedAt": self.stored_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReflectionResult:
        root_cause = data.get("rootCause", {})
        return cls(
            result_id=str(data["resultId"]),
            reflection_id=str(data.get("reflectionId", "")),
            outcome_id=str(data.get("outcomeId", "")),
            root_cause_category=str(root_cause.get("category", "")),
            root_cause_confidence=float(root_cause.get("confidence", 1.0)),
            insights=tuple(str(i) for i in data.get("insights") or []),
            planner_adjustments=tuple(
                PlannerAdjustment.from_dict(a) for a in data.get("plannerAdjustments") or []
            ),
            stored_at=str(data.get("storedAt", "")),
        )


@dataclass(frozen=True, slots=True)
class EvaluationScore:
    """Record of plan evaluation scores."""

    score_id: str
    plan_id: str = ""
    safety_score: float = 1.0
    cost_estimate: float = 0.0
    complexity_score: float = 0.0
    confidence_level: float = 1.0
    goal_alignment: float = 1.0
    outcome_score: float = 0.0  # How well did it actually do?
    prediction_accuracy: float = 0.0  # How accurate were predictions?
    stored_at: str = ""  # ISO8601

    def to_dict(self) -> dict[str, Any]:
        return {
            "scoreId": self.score_id,
            "planId": self.plan_id,
            "safetyScore": self.safety_score,
            "costEstimate": self.cost_estimate,
            "complexityScore": self.complexity_score,
            "confidenceLevel": self.confidence_level,
            "goalAlignment": self.goal_alignment,
            "outcomeScore": self.outcome_score,
            "predictionAccuracy": self.prediction_accuracy,
            "storedAt": self.stored_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationScore:
        return cls(
            score_id=str(data["scoreId"]),
            plan_id=str(data.get("planId", "")),
            safety_score=float(data.get("safetyScore", 1.0)),
            cost_estimate=float(data.get("costEstimate", 0.0)),
            complexity_score=float(data.get("complexityScore", 0.0)),
            confidence_level=float(data.get("confidenceLevel", 1.0)),
            goal_alignment=float(data.get("goalAlignment", 1.0)),
            outcome_score=float(data.get("outcomeScore", 0.0)),
            prediction_accuracy=float(data.get("predictionAccuracy", 0.0)),
            stored_at=str(data.get("storedAt", "")),
        )


@dataclass(frozen=True, slots=True)
class ReplanHistory:
    """Record of replanning attempts."""

    replan_id: str
    original_plan_id: str = ""
    new_plan_id: str = ""
    replan_reason: str = ""  # action_failed, constraint_violated
    attempt_number: int = 1
    max_attempts: int = 3
    outcome: str = ""  # success, failure
    improvement: float = 0.0
    stored_at: str = ""  # ISO8601

    def to_dict(self) -> dict[str, Any]:
        return {
            "replanId": self.replan_id,
            "originalPlanId": self.original_plan_id,
            "newPlanId": self.new_plan_id,
            "replanReason": self.replan_reason,
            "attemptNumber": self.attempt_number,
            "maxAttempts": self.max_attempts,
            "outcome": self.outcome,
            "improvement": self.improvement,
            "storedAt": self.stored_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReplanHistory:
        return cls(
            replan_id=str(data["replanId"]),
            original_plan_id=str(data.get("originalPlanId", "")),
            new_plan_id=str(data.get("newPlanId", "")),
            replan_reason=str(data.get("replanReason", "")),
            attempt_number=int(data.get("attemptNumber", 1)),
            max_attempts=int(data.get("maxAttempts", 3)),
            outcome=str(data.get("outcome", "")),
            improvement=float(data.get("improvement", 0.0)),
            stored_at=str(data.get("storedAt", "")),
        )


@dataclass(frozen=True, slots=True)
class MemoryRetrievalQuery:
    """Query for retrieving from planner memory."""

    goal_pattern: str = ""
    context: ContextSnapshot = field(default_factory=ContextSnapshot)
    similarity_threshold: float = 0.7
    max_results: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "goalPattern": self.goal_pattern,
            "context": self.context.to_dict(),
            "similarityThreshold": self.similarity_threshold,
            "maxResults": self.max_results,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryRetrievalQuery:
        return cls(
            goal_pattern=str(data.get("goalPattern", "")),
            context=ContextSnapshot.from_dict(data.get("context") or {}),
            similarity_threshold=float(data.get("similarityThreshold", 0.7)),
            max_results=int(data.get("maxResults", 10)),
        )


# Memory limits from spec
MEMORY_LIMITS = {
    "max_patterns": 10000,
    "max_goal_outcomes": 50000,
    "max_reflection_results": 25000,
    "max_evaluation_scores": 50000,
    "total_storage_mb": 500,
}

# Retrieval weights from spec
RETRIEVAL_WEIGHTS = {
    "similarity": 0.4,
    "recency": 0.2,
    "usage": 0.2,
    "success": 0.2,
}

# Decay thresholds from spec
DECAY_THRESHOLDS = {
    "eviction": 0.1,
    "warning": 0.3,
    "refresh": 0.5,
}

# Retention periods from spec (in days)
RETENTION_PERIODS = {
    "recent_goals": 90,
    "successful_patterns": 365,
    "failed_patterns": 180,
    "evaluation_scores": 180,
    "reflection_insights": 365,
}
