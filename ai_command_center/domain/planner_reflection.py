"""Reflection Engine — learning from execution outcomes.

This module defines the reflection mechanisms that enable the planner
to learn from past outcomes and improve future planning.
Per ACC Planner Constitution Phase C0:
- 07_REFLECTION_ENGINE_SPEC.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OutcomeType(Enum):
    """Type of execution outcome."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class RootCauseCategory(Enum):
    """Categories of root causes."""

    STATE_MISUNDERSTANDING = "state_misunderstanding"
    CONSTRAINT_VIOLATION = "constraint_violation"
    CAPABILITY_LIMITATION = "capability_limitation"
    DEPENDENCY_ISSUE = "dependency_issue"
    ENVIRONMENTAL = "environmental"
    UNKNOWN = "unknown"


class ReflectionType(Enum):
    """Type of reflection."""

    SUCCESS_ANALYSIS = "success"
    FAILURE_ANALYSIS = "failure"
    PARTIAL_SUCCESS_ANALYSIS = "partial"


@dataclass(frozen=True, slots=True)
class ActionSummary:
    """Summary of an action execution."""

    action_id: str = ""
    action_label: str = ""
    status: str = ""  # succeeded, failed, skipped
    error_message: str = ""
    duration: str = ""  # e.g., "5s"

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionId": self.action_id,
            "actionLabel": self.action_label,
            "status": self.status,
            "errorMessage": self.error_message,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionSummary:
        return cls(
            action_id=str(data.get("actionId", "")),
            action_label=str(data.get("actionLabel", "")),
            status=str(data.get("status", "")),
            error_message=str(data.get("errorMessage", "")),
            duration=str(data.get("duration", "")),
        )


@dataclass(frozen=True, slots=True)
class OutcomeSummary:
    """Summary of plan execution outcome."""

    actions_executed: int = 0
    actions_succeeded: int = 0
    actions_failed: int = 0
    actions_skipped: int = 0
    duration: str = ""  # e.g., "5m"
    resources_used: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionsExecuted": self.actions_executed,
            "actionsSucceeded": self.actions_succeeded,
            "actionsFailed": self.actions_failed,
            "actionsSkipped": self.actions_skipped,
            "duration": self.duration,
            "resourcesUsed": dict(self.resources_used),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutcomeSummary:
        return cls(
            actions_executed=int(data.get("actionsExecuted", 0)),
            actions_succeeded=int(data.get("actionsSucceeded", 0)),
            actions_failed=int(data.get("actionsFailed", 0)),
            actions_skipped=int(data.get("actionsSkipped", 0)),
            duration=str(data.get("duration", "")),
            resources_used=dict(data.get("resourcesUsed") or {}),
        )


@dataclass(frozen=True, slots=True)
class SuccessFactor:
    """A factor that contributed to success."""

    factor: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": self.factor,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SuccessFactor:
        return cls(
            factor=str(data.get("factor", "")),
            confidence=float(data.get("confidence", 1.0)),
        )


@dataclass(frozen=True, slots=True)
class ContributingFactor:
    """A factor that contributed to failure."""

    factor: str = ""
    confidence: float = 1.0
    impact: str = "medium"  # high, medium, low

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": self.factor,
            "confidence": self.confidence,
            "impact": self.impact,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContributingFactor:
        return cls(
            factor=str(data.get("factor", "")),
            confidence=float(data.get("confidence", 1.0)),
            impact=str(data.get("impact", "medium")),
        )


@dataclass(frozen=True, slots=True)
class FailurePoint:
    """Information about where failure occurred."""

    action_id: str = ""
    action_label: str = ""
    failure_type: str = ""  # EXECUTION_ERROR, etc.
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionId": self.action_id,
            "actionLabel": self.action_label,
            "failureType": self.failure_type,
            "errorMessage": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailurePoint:
        return cls(
            action_id=str(data.get("actionId", "")),
            action_label=str(data.get("actionLabel", "")),
            failure_type=str(data.get("failureType", "")),
            error_message=str(data.get("errorMessage", "")),
        )


@dataclass(frozen=True, slots=True)
class RootCause:
    """Root cause of an outcome."""

    category: RootCauseCategory
    description: str = ""
    confidence: float = 1.0
    evidence: tuple[str, ...] = field(default_factory=tuple)
    needs_escalation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "needsEscalation": self.needs_escalation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RootCause:
        try:
            category = RootCauseCategory(data.get("category", RootCauseCategory.UNKNOWN.value))
        except ValueError:
            category = RootCauseCategory.UNKNOWN

        return cls(
            category=category,
            description=str(data.get("description", "")),
            confidence=float(data.get("confidence", 1.0)),
            evidence=tuple(str(e) for e in data.get("evidence") or []),
            needs_escalation=bool(data.get("needsEscalation", False)),
        )


@dataclass(frozen=True, slots=True)
class SuccessAnalysis:
    """Analysis of a successful plan execution."""

    outcome: OutcomeType = OutcomeType.SUCCESS
    goal_id: str = ""
    plan_id: str = ""
    summary: OutcomeSummary = field(default_factory=OutcomeSummary)
    success_factors: tuple[SuccessFactor, ...] = field(default_factory=tuple)
    reproducible_patterns: tuple[str, ...] = field(default_factory=tuple)
    potential_optimizations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "goalId": self.goal_id,
            "planId": self.plan_id,
            "summary": self.summary.to_dict(),
            "successFactors": [f.to_dict() for f in self.success_factors],
            "reproduciblePatterns": list(self.reproducible_patterns),
            "potentialOptimizations": list(self.potential_optimizations),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SuccessAnalysis:
        try:
            outcome = OutcomeType(data.get("outcome", OutcomeType.SUCCESS.value))
        except ValueError:
            outcome = OutcomeType.SUCCESS

        return cls(
            outcome=outcome,
            goal_id=str(data.get("goalId", "")),
            plan_id=str(data.get("planId", "")),
            summary=OutcomeSummary.from_dict(data.get("summary") or {}),
            success_factors=tuple(
                SuccessFactor.from_dict(f) for f in data.get("successFactors") or []
            ),
            reproducible_patterns=tuple(
                str(p) for p in data.get("reproduciblePatterns") or []
            ),
            potential_optimizations=tuple(
                str(o) for o in data.get("potentialOptimizations") or []
            ),
        )


@dataclass(frozen=True, slots=True)
class FailureAnalysis:
    """Analysis of a failed plan execution."""

    outcome: OutcomeType = OutcomeType.FAILURE
    goal_id: str = ""
    plan_id: str = ""
    failure_point: FailurePoint = field(default_factory=FailurePoint)
    root_cause: RootCause = field(default_factory=lambda: RootCause(category=RootCauseCategory.UNKNOWN))
    contributing_factors: tuple[ContributingFactor, ...] = field(default_factory=tuple)
    lesson: str = ""
    planner_improvement: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "goalId": self.goal_id,
            "planId": self.plan_id,
            "failurePoint": self.failure_point.to_dict(),
            "rootCause": self.root_cause.to_dict(),
            "contributingFactors": [f.to_dict() for f in self.contributing_factors],
            "lesson": self.lesson,
            "plannerImprovement": self.planner_improvement,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailureAnalysis:
        try:
            outcome = OutcomeType(data.get("outcome", OutcomeType.FAILURE.value))
        except ValueError:
            outcome = OutcomeType.FAILURE

        return cls(
            outcome=outcome,
            goal_id=str(data.get("goalId", "")),
            plan_id=str(data.get("planId", "")),
            failure_point=FailurePoint.from_dict(data.get("failurePoint") or {}),
            root_cause=RootCause.from_dict(data.get("rootCause") or {}),
            contributing_factors=tuple(
                ContributingFactor.from_dict(f)
                for f in data.get("contributingFactors") or []
            ),
            lesson=str(data.get("lesson", "")),
            planner_improvement=str(data.get("plannerImprovement", "")),
        )


@dataclass(frozen=True, slots=True)
class PartialSuccessAnalysis:
    """Analysis of a partially successful plan execution."""

    outcome: OutcomeType = OutcomeType.PARTIAL
    goal_id: str = ""
    plan_id: str = ""
    actions_completed: int = 0
    actions_total: int = 0
    completion_percentage: float = 0.0
    uncompleted_actions: tuple[str, ...] = field(default_factory=tuple)
    what_worked: tuple[str, ...] = field(default_factory=tuple)
    what_failed: tuple[str, ...] = field(default_factory=tuple)
    why_partially_completed: str = ""
    partial_value: str = ""
    remaining_value: str = ""
    recovery_suggestions: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "goalId": self.goal_id,
            "planId": self.plan_id,
            "completion": {
                "actionsCompleted": self.actions_completed,
                "actionsTotal": self.actions_total,
                "completionPercentage": self.completion_percentage,
            },
            "uncompletedActions": list(self.uncompleted_actions),
            "whatWorked": list(self.what_worked),
            "whatFailed": list(self.what_failed),
            "whyPartiallyCompleted": self.why_partially_completed,
            "partialValue": self.partial_value,
            "remainingValue": self.remaining_value,
            "recoverySuggestions": list(self.recovery_suggestions),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PartialSuccessAnalysis:
        try:
            outcome = OutcomeType(data.get("outcome", OutcomeType.PARTIAL.value))
        except ValueError:
            outcome = OutcomeType.PARTIAL

        completion = data.get("completion", {})

        return cls(
            outcome=outcome,
            goal_id=str(data.get("goalId", "")),
            plan_id=str(data.get("planId", "")),
            actions_completed=int(completion.get("actionsCompleted", 0)),
            actions_total=int(completion.get("actionsTotal", 0)),
            completion_percentage=float(completion.get("completionPercentage", 0.0)),
            uncompleted_actions=tuple(str(a) for a in data.get("uncompletedActions") or []),
            what_worked=tuple(str(w) for w in data.get("whatWorked") or []),
            what_failed=tuple(str(w) for w in data.get("whatFailed") or []),
            why_partially_completed=str(data.get("whyPartiallyCompleted", "")),
            partial_value=str(data.get("partialValue", "")),
            remaining_value=str(data.get("remainingValue", "")),
            recovery_suggestions=tuple(
                str(s) for s in data.get("recoverySuggestions") or []
            ),
        )


@dataclass(frozen=True, slots=True)
class Insight:
    """An insight from reflection."""

    insight_type: str = ""  # what_went_well, what_to_improve, actionable_change
    description: str = ""
    applicability: tuple[str, ...] = field(default_factory=tuple)
    target: str = ""  # planner, runtime, etc.

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.insight_type,
            "description": self.description,
            "applicability": list(self.applicability),
            "target": self.target,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Insight:
        return cls(
            insight_type=str(data.get("type", "")),
            description=str(data.get("description", "")),
            applicability=tuple(str(a) for a in data.get("applicability") or []),
            target=str(data.get("target", "")),
        )


@dataclass(frozen=True, slots=True)
class Recommendation:
    """A recommendation from reflection."""

    recommendation_type: str = ""  # replan_with_changes, add_precondition, etc.
    changes: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.recommendation_type,
            "changes": list(self.changes),
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Recommendation:
        return cls(
            recommendation_type=str(data.get("type", "")),
            changes=tuple(dict(c) for c in data.get("changes") or []),
            rationale=str(data.get("rationale", "")),
        )


@dataclass(frozen=True, slots=True)
class MemoryUpdate:
    """Instructions for updating planner memory."""

    store_pattern: dict[str, Any] | None = None
    update_strategy: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "storePattern": self.store_pattern,
            "updateStrategy": self.update_strategy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryUpdate:
        return cls(
            store_pattern=data.get("storePattern"),
            update_strategy=data.get("updateStrategy"),
        )


@dataclass(frozen=True, slots=True)
class ReflectionFeedback:
    """Complete reflection feedback for the planner."""

    feedback_id: str
    goal_id: str = ""
    plan_id: str = ""
    reflection_type: ReflectionType = ReflectionType.SUCCESS_ANALYSIS
    root_cause: RootCause | None = None
    insights: tuple[Insight, ...] = field(default_factory=tuple)
    recommendations: tuple[Recommendation, ...] = field(default_factory=tuple)
    memory_update: MemoryUpdate = field(default_factory=MemoryUpdate)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedbackId": self.feedback_id,
            "goalId": self.goal_id,
            "planId": self.plan_id,
            "reflectionType": self.reflection_type.value,
            "rootCause": self.root_cause.to_dict() if self.root_cause else None,
            "insights": [i.to_dict() for i in self.insights],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "memoryUpdate": self.memory_update.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReflectionFeedback:
        try:
            reflection_type = ReflectionType(
                data.get("reflectionType", ReflectionType.SUCCESS_ANALYSIS.value)
            )
        except ValueError:
            reflection_type = ReflectionType.SUCCESS_ANALYSIS

        root_cause = data.get("rootCause")
        return cls(
            feedback_id=str(data["feedbackId"]),
            goal_id=str(data.get("goalId", "")),
            plan_id=str(data.get("planId", "")),
            reflection_type=reflection_type,
            root_cause=RootCause.from_dict(root_cause) if root_cause else None,
            insights=tuple(Insight.from_dict(i) for i in data.get("insights") or []),
            recommendations=tuple(
                Recommendation.from_dict(r) for r in data.get("recommendations") or []
            ),
            memory_update=MemoryUpdate.from_dict(data.get("memoryUpdate") or {}),
        )


# Reflection triggers from spec
REFLECTION_TRIGGERS = {
    "always": ["goal_completed", "goal_failed", "goal_abandoned"],
    "on_request": ["planner_requests_reflection", "human_requests_reflection"],
    "periodic": ["session_summary"],
}

# Replan limits from spec
REPLAN_LIMITS = {
    "max_replan_attempts": 3,
    "max_reflection_cycles": 5,
}

# Minimum confidence threshold for root cause detection
ROOT_CAUSE_MIN_CONFIDENCE = 0.5
