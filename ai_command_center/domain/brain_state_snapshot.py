"""Domain snapshot: typed projection of Brain Kernel state.

Phase 11 — BrainStateSnapshot
Consolidates the five raw str/dict AppState brain fields into a single
immutable snapshot. All raw fields are preserved for backward-compat;
this snapshot is the canonical view for UI and services.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "GoalSnapshot",
    "ObservationSnapshot",
    "RuntimeActionSnapshot",
    "PlanStepSnapshot",
    "PlanSnapshot",
    "BrainStateSnapshot",
]

_MAX_GOAL_HISTORY: int = 20
_MAX_OBSERVATION_HISTORY: int = 30
_MAX_ACTION_HISTORY: int = 50


@dataclass(frozen=True, slots=True)
class GoalSnapshot:
    """Typed projection of a single brain goal."""

    goal_id: str = ""
    text: str = ""
    status: str = "pending"
    priority: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    error: str = ""
    meta: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "GoalSnapshot":
        meta_raw = raw.get("meta", {})
        meta: tuple[tuple[str, str], ...] = ()
        if isinstance(meta_raw, dict):
            meta = tuple((str(k), str(v)) for k, v in meta_raw.items())
        return cls(
            goal_id=str(raw.get("goal_id", raw.get("id", ""))),
            text=str(raw.get("text", raw.get("goal", ""))),
            status=str(raw.get("status", "pending")),
            priority=int(raw.get("priority", 0)),
            created_at=float(raw.get("created_at", 0.0)),
            updated_at=float(raw.get("updated_at", 0.0)),
            error=str(raw.get("error", "")),
            meta=meta,
        )


@dataclass(frozen=True, slots=True)
class ObservationSnapshot:
    """Typed projection of a single brain observation."""

    observation_id: str = ""
    content: str = ""
    source: str = ""
    confidence: float = 1.0
    timestamp: float = 0.0
    meta: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "ObservationSnapshot":
        meta_raw = raw.get("meta", {})
        meta: tuple[tuple[str, str], ...] = ()
        if isinstance(meta_raw, dict):
            meta = tuple((str(k), str(v)) for k, v in meta_raw.items())
        return cls(
            observation_id=str(raw.get("observation_id", raw.get("id", ""))),
            content=str(raw.get("content", raw.get("text", ""))),
            source=str(raw.get("source", "")),
            confidence=float(raw.get("confidence", 1.0)),
            timestamp=float(raw.get("timestamp", 0.0)),
            meta=meta,
        )


@dataclass(frozen=True, slots=True)
class RuntimeActionSnapshot:
    """Typed projection of a single runtime action."""

    action_id: str = ""
    action_type: str = ""
    status: str = "started"
    result: str = ""
    error: str = ""
    timestamp: float = 0.0
    meta: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "RuntimeActionSnapshot":
        meta_raw = raw.get("meta", {})
        meta: tuple[tuple[str, str], ...] = ()
        if isinstance(meta_raw, dict):
            meta = tuple((str(k), str(v)) for k, v in meta_raw.items())
        return cls(
            action_id=str(raw.get("action_id", raw.get("id", ""))),
            action_type=str(raw.get("action_type", raw.get("type", ""))),
            status=str(raw.get("status", "started")),
            result=str(raw.get("result", "")),
            error=str(raw.get("error", "")),
            timestamp=float(raw.get("timestamp", 0.0)),
            meta=meta,
        )


@dataclass(frozen=True, slots=True)
class PlanStepSnapshot:
    """Typed projection of a single plan step."""

    step_id: str = ""
    description: str = ""
    status: str = "pending"
    index: int = 0

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "PlanStepSnapshot":
        return cls(
            step_id=str(raw.get("step_id", raw.get("id", ""))),
            description=str(raw.get("description", raw.get("text", ""))),
            status=str(raw.get("status", "pending")),
            index=int(raw.get("index", raw.get("order", 0))),
        )


@dataclass(frozen=True, slots=True)
class PlanSnapshot:
    """Typed projection of the planner's last plan."""

    plan_id: str = ""
    goal: str = ""
    steps: tuple[PlanStepSnapshot, ...] = ()
    status: str = "pending"
    created_at: float = 0.0

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "PlanSnapshot":
        raw_steps = raw.get("steps", ())
        steps: tuple[PlanStepSnapshot, ...] = ()
        if isinstance(raw_steps, (list, tuple)):
            steps = tuple(
                PlanStepSnapshot.from_dict(s) if isinstance(s, dict) else PlanStepSnapshot()
                for s in raw_steps
            )
        return cls(
            plan_id=str(raw.get("plan_id", raw.get("id", ""))),
            goal=str(raw.get("goal", "")),
            steps=steps,
            status=str(raw.get("status", "pending")),
            created_at=float(raw.get("created_at", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class BrainStateSnapshot:
    """Consolidated typed projection of all Brain Kernel AppState fields.

    Phase 11 deliverable — replaces five raw str/dict fields with a
    single immutable snapshot. The raw fields on AppState are kept for
    backward compatibility; this snapshot is the authoritative view.
    """

    kernel_state: str = "boot"
    recent_goals: tuple[GoalSnapshot, ...] = ()
    recent_observations: tuple[ObservationSnapshot, ...] = ()
    recent_runtime_actions: tuple[RuntimeActionSnapshot, ...] = ()
    last_plan: PlanSnapshot = field(default_factory=PlanSnapshot)
    revision: int = 0

    def with_kernel_state(self, new_state: str) -> "BrainStateSnapshot":
        """Return a new snapshot with updated kernel state."""
        from dataclasses import replace as _replace
        return _replace(self, kernel_state=new_state, revision=self.revision + 1)

    def with_goal(self, goal: GoalSnapshot) -> "BrainStateSnapshot":
        """Prepend goal and trim to cap."""
        from dataclasses import replace as _replace
        updated = (goal, *self.recent_goals)[:_MAX_GOAL_HISTORY]
        return _replace(self, recent_goals=updated, revision=self.revision + 1)

    def with_observation(self, obs: ObservationSnapshot) -> "BrainStateSnapshot":
        """Prepend observation and trim to cap."""
        from dataclasses import replace as _replace
        updated = (obs, *self.recent_observations)[:_MAX_OBSERVATION_HISTORY]
        return _replace(self, recent_observations=updated, revision=self.revision + 1)

    def with_action(self, action: RuntimeActionSnapshot) -> "BrainStateSnapshot":
        """Prepend runtime action and trim to cap."""
        from dataclasses import replace as _replace
        updated = (action, *self.recent_runtime_actions)[:_MAX_ACTION_HISTORY]
        return _replace(self, recent_runtime_actions=updated, revision=self.revision + 1)

    def with_plan(self, plan: PlanSnapshot) -> "BrainStateSnapshot":
        """Return a new snapshot with updated last plan."""
        from dataclasses import replace as _replace
        return _replace(self, last_plan=plan, revision=self.revision + 1)