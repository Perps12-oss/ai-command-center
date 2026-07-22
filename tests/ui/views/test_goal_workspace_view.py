"""UI tests for PR-UI-E07 Goal Workspace."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_GOAL_OPEN,
    UI_GOAL_SELECT,
    UI_GOAL_TASK_SELECT,
)
from ai_command_center.domain.brain_state_snapshot import (
    BrainStateSnapshot,
    GoalSnapshot,
    PlanSnapshot,
    PlanStepSnapshot,
)
from ai_command_center.core.state.inspector_state import resolve_inspect_navigate_view
from ai_command_center.ui.controller import UIController
from tests.ui.fake_ui import (
    GoalDetail,
    GoalTree,
    GoalView,
    InspectorHost,
    SuccessCriteriaCard,
    TaskRow,
)


def _snap() -> AppState:
    return AppState(
        brain_state=BrainStateSnapshot(
            kernel_state="ready",
            recent_goals=(
                GoalSnapshot(
                    goal_id="g1",
                    text="Ship E07",
                    status="active",
                    priority=2,
                    meta=(("success_criteria", "Tree + tasks visible"),),
                ),
                GoalSnapshot(goal_id="g2", text="Backlog", status="queued", priority=0),
            ),
            last_plan=PlanSnapshot(
                plan_id="p1",
                goal="Ship E07",
                status="running",
                steps=(
                    PlanStepSnapshot(step_id="s1", description="Tree", status="done"),
                    PlanStepSnapshot(step_id="s2", description="Tasks", status="running"),
                ),
            ),
        )
    )


def test_goal_workspace_projects_tree_tasks_criteria():
    inspected: list[object] = []
    tasks: list[tuple[str, str]] = []
    view = GoalView(
        None,
        on_select_task=lambda g, t: tasks.append((g, t)),
        on_inspect_select=lambda ref: inspected.append(ref),
    )
    view.apply_state(_snap())
    assert "1 active" in view._metrics.cget("text")
    assert "Ship E07" in view._hero_hint.cget("text")
    assert view._tree is not None
    assert view._workspace_detail is not None
    assert len(view._tasks_scroll.winfo_children()) >= 2

    view._select("g1")
    assert view._selected_goal_id == "g1"
    assert inspected and getattr(inspected[-1], "kind") == "goal"

    view._select_task("s2")
    assert tasks == [("g1", "s2")]
    assert getattr(inspected[-1], "kind") == "task"
    assert resolve_inspect_navigate_view("task") == "goals"

    host = InspectorHost(None)
    host.show(inspected[-1])
    assert host._current_ref is not None
    assert host._current_ref.kind == "task"
    assert "Tasks" in host._title.cget("text") or host._title.cget("text")


def test_goal_tree_and_criteria_components():
    selected: list[str] = []
    tree = GoalTree(None, on_select=lambda gid: selected.append(gid))
    tree.apply_snapshot(
        (
            GoalSnapshot(goal_id="g1", text="A", status="active"),
            GoalSnapshot(goal_id="g2", text="B", status="completed"),
        ),
        selected_goal_id="g1",
    )
    assert selected == []
    TaskRow(None, step_id="s1", description="Do", status="pending", on_select=lambda s: selected.append(s))._click()
    assert "s1" in selected

    card = SuccessCriteriaCard(None)
    card.apply_snapshot(
        GoalSnapshot(goal_id="g1", meta=(("success_criteria", "done"),)),
        PlanSnapshot(steps=(PlanStepSnapshot(step_id="s1", status="done"),)),
    )
    detail = GoalDetail(None)
    detail.apply_snapshot(GoalSnapshot(goal_id="g1", text="X", status="active"))


def test_controller_goal_intents():
    bus = EventBus()
    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[str] = []
    bus.subscribe(UI_GOAL_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_GOAL_TASK_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_GOAL_OPEN, lambda e: seen.append(e.topic))
    controller.publish_goal_select("g1")
    controller.publish_goal_task_select("g1", "s1")
    controller.publish_goal_open()
    assert seen == [UI_GOAL_SELECT, UI_GOAL_TASK_SELECT, UI_GOAL_OPEN]
