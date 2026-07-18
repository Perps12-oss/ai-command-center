"""Goal Dashboard planner_last_plan fallback and empty-plan projection tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.brain_state_snapshot import (
    BrainStateSnapshot,
    GoalSnapshot,
    PlanSnapshot,
    PlanStepSnapshot,
)
from ai_command_center.ui.views.goal_dashboard.goal_sorting import resolve_plan
from tests.ui.fake_ui import GoalView


def test_resolve_plan_prefers_brain_last_plan() -> None:
    brain = BrainStateSnapshot(
        last_plan=PlanSnapshot(
            plan_id="brain",
            goal="From brain",
            steps=(PlanStepSnapshot(step_id="s1", description="A", status="pending"),),
        )
    )
    plan = resolve_plan(brain, {"goal": "legacy", "steps": [{"description": "B"}]})
    assert isinstance(plan, PlanSnapshot)
    assert plan.goal == "From brain"
    assert plan.plan_id == "brain"


def test_resolve_plan_falls_back_to_planner_last_plan() -> None:
    brain = BrainStateSnapshot(last_plan=PlanSnapshot())
    plan = resolve_plan(
        brain,
        {
            "goal": "Legacy planner goal",
            "steps": [
                {"step_id": "p1", "description": "Legacy step", "status": "running"},
            ],
        },
    )
    assert isinstance(plan, PlanSnapshot)
    assert plan.goal == "Legacy planner goal"
    assert len(plan.steps) == 1
    assert plan.steps[0].description == "Legacy step"


def test_goal_view_uses_planner_last_plan_fallback() -> None:
    snap = AppState(
        brain_state=BrainStateSnapshot(
            recent_goals=(
                GoalSnapshot(goal_id="g1", text="Active", status="active", priority=1),
            ),
            last_plan=PlanSnapshot(),
        ),
        planner_last_plan={
            "goal": "Fallback plan",
            "steps": [
                {"step_id": "s1", "description": "Do work", "status": "completed"},
                {"step_id": "s2", "description": "Verify", "status": "pending"},
            ],
        },
    )
    view = GoalView(None)
    view.apply_state(snap)
    assert "Fallback plan" in view._plan._goal.cget("text")
    assert "1/2" in view._progress._label.cget("text") or "50%" in view._progress._label.cget(
        "text"
    )
