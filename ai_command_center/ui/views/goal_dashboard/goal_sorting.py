"""Goal list sort/filter helpers from projected GoalSnapshot fields only."""

from __future__ import annotations

from ai_command_center.domain.brain_state_snapshot import GoalSnapshot

_STATUS_RANK = {
    "active": 0,
    "running": 0,
    "in_progress": 0,
    "queued": 1,
    "pending": 1,
    "paused": 2,
    "blocked": 2,
    "waiting": 2,
    "failed": 3,
    "error": 3,
    "complete": 4,
    "completed": 4,
    "success": 4,
    "done": 4,
    "cancelled": 5,
    "canceled": 5,
}

FILTER_OPTIONS = (
    "all",
    "active",
    "queued",
    "paused",
    "completed",
    "failed",
    "cancelled",
)


def normalize_goal_status(status: str) -> str:
    s = str(status or "").strip().lower()
    if s in {"running", "in_progress"}:
        return "active"
    if s in {"pending"}:
        return "queued"
    if s in {"completed", "success", "done"}:
        return "completed"
    if s in {"canceled"}:
        return "cancelled"
    if s in {"error"}:
        return "failed"
    return s or "queued"


def sort_goals(goals: list[GoalSnapshot]) -> list[GoalSnapshot]:
    """Operator sort: Active → Queued → Paused → Failed → Completed → Cancelled."""
    return sorted(
        goals,
        key=lambda g: (
            _STATUS_RANK.get(normalize_goal_status(g.status), 9),
            -int(g.priority or 0),
            -float(g.updated_at or g.created_at or 0.0),
            g.goal_id,
        ),
    )


def filter_goals(goals: list[GoalSnapshot], status_filter: str) -> list[GoalSnapshot]:
    key = str(status_filter or "all").strip().lower()
    if key in {"", "all"}:
        return list(goals)
    return [g for g in goals if normalize_goal_status(g.status) == key]


def count_by_bucket(goals: list[GoalSnapshot]) -> dict[str, int]:
    counts = {"active": 0, "queued": 0, "paused": 0, "failed": 0}
    for g in goals:
        bucket = normalize_goal_status(g.status)
        if bucket in counts:
            counts[bucket] += 1
    return counts


def highest_priority_active(goals: list[GoalSnapshot]) -> GoalSnapshot | None:
    active = [g for g in goals if normalize_goal_status(g.status) == "active"]
    if not active:
        return None
    return sorted(active, key=lambda g: (-int(g.priority or 0), g.text or g.goal_id))[0]


def resolve_plan(brain_state: object, planner_last_plan: object) -> object:
    """Prefer brain_state.last_plan; fall back to planner_last_plan dict."""
    from ai_command_center.domain.brain_state_snapshot import PlanSnapshot

    last = getattr(brain_state, "last_plan", None)
    if isinstance(last, PlanSnapshot) and (last.goal or last.steps):
        return last
    if isinstance(planner_last_plan, dict) and planner_last_plan:
        return PlanSnapshot.from_dict(planner_last_plan)
    if isinstance(last, PlanSnapshot):
        return last
    return PlanSnapshot()
