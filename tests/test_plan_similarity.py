"""Stuck-loop / plan similarity (ADR-019 M4)."""

from __future__ import annotations

from ai_command_center.core.plan_similarity import is_stuck, jaccard_similarity, serialize_plan
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep


def test_jaccard_identical() -> None:
    assert jaccard_similarity("a b c", "a b c") == 1.0


def test_is_stuck_on_near_duplicates() -> None:
    plan = ExecutionPlan(
        goal="echo",
        steps=(PlanStep(step_id="1", capability="shell", args={"command": "echo"}),),
    )
    s = serialize_plan(plan)
    assert is_stuck([s, s, s])
    assert not is_stuck([s, s])


def test_is_stuck_false_when_plans_differ() -> None:
    a = serialize_plan(
        ExecutionPlan(
            goal="a",
            steps=(PlanStep(step_id="1", capability="shell", args={"command": "echo a"}),),
        )
    )
    b = serialize_plan(
        ExecutionPlan(
            goal="b",
            steps=(
                PlanStep(step_id="1", capability="launch_application", args={"application": "calc"}),
            ),
        )
    )
    c = serialize_plan(
        ExecutionPlan(
            goal="c",
            steps=(PlanStep(step_id="1", capability="create_note", args={"title": "x"}),),
        )
    )
    assert not is_stuck([a, b, c])
