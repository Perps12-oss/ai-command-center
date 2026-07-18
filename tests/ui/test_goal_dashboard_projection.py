"""Projection tests for Phase 11F Goal Dashboard workspace."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import GOAL_SUBMIT_REQUEST
from ai_command_center.domain.brain_state_snapshot import (
    BrainStateSnapshot,
    GoalSnapshot,
    PlanSnapshot,
    PlanStepSnapshot,
)
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.goal_dashboard.goal_progress_panel import plan_progress
from ai_command_center.ui.views.goal_dashboard.goal_sorting import (
    filter_goals,
    highest_priority_active,
    normalize_goal_status,
    sort_goals,
)
from tests.ui.fake_ui import GoalView

ROOT = Path(__file__).resolve().parents[2]


def _goals() -> tuple[GoalSnapshot, ...]:
    return (
        GoalSnapshot(goal_id="g-active", text="Ship feature", status="active", priority=2),
        GoalSnapshot(goal_id="g-queued", text="Backlog item", status="queued", priority=1),
        GoalSnapshot(goal_id="g-paused", text="Paused work", status="paused", priority=3),
        GoalSnapshot(goal_id="g-failed", text="Broken goal", status="failed", priority=0, error="boom"),
        GoalSnapshot(goal_id="g-done", text="Finished", status="completed", priority=0),
    )


def _sample_snap(*, empty: bool = False) -> AppState:
    if empty:
        return AppState(brain_state=BrainStateSnapshot())
    plan = PlanSnapshot(
        plan_id="p1",
        goal="Ship feature",
        status="running",
        steps=(
            PlanStepSnapshot(step_id="s1", description="Plan", status="completed", index=0),
            PlanStepSnapshot(step_id="s2", description="Build", status="running", index=1),
            PlanStepSnapshot(step_id="s3", description="Verify", status="pending", index=2),
        ),
    )
    return AppState(
        brain_state=BrainStateSnapshot(recent_goals=_goals(), last_plan=plan, kernel_state="ready"),
        planner_last_plan={"goal": "legacy", "steps": []},
    )


def test_hero_metrics_and_highest_priority() -> None:
    view = GoalView(None)
    view.apply_state(_sample_snap())
    metrics = view._metrics.cget("text")
    assert "1 active" in metrics
    assert "1 queued" in metrics
    assert "1 paused" in metrics
    assert "1 failed" in metrics
    assert "Ship feature" in view._hero_hint.cget("text")
    assert view._hero_action.cget("text") == "New Goal"
    assert view._surface_state.cget("text") == ""


def test_goal_sorting_and_filtering() -> None:
    ordered = [normalize_goal_status(g.status) for g in sort_goals(list(_goals()))]
    assert ordered[0] == "active"
    assert "failed" in ordered
    assert ordered.index("failed") < ordered.index("completed")
    filtered = filter_goals(list(_goals()), "paused")
    assert len(filtered) == 1 and filtered[0].goal_id == "g-paused"
    top = highest_priority_active(list(_goals()))
    assert top is not None and top.goal_id == "g-active"


def test_detail_plan_progress_history() -> None:
    view = GoalView(None)
    view.apply_state(_sample_snap())
    view._select("g-failed")
    detail_texts: list[str] = []
    for child in view._detail._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    detail_texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    assert any("boom" in t for t in detail_texts)
    assert "Ship feature" in view._plan._goal.cget("text")
    done, total, fraction, label = plan_progress(_sample_snap().brain_state.last_plan)
    assert (done, total) == (1, 3)
    assert "1/3" in label
    assert "33%" in view._progress._label.cget("text") or "1/3" in view._progress._label.cget("text")
    assert view._history._count.cget("text") == "5"


def test_empty_states() -> None:
    view = GoalView(None)
    view.apply_state(_sample_snap(empty=True))
    surface = view._surface_state.cget("text")
    assert "No goals" in surface or "brain_state" in surface
    assert "Next:" in surface
    assert "No Data" not in surface


def test_new_goal_publishes_goal_submit_request() -> None:
    bus = EventBus()
    ctrl = UIController(bus, AppStateStore(bus), on_state=lambda: None)
    seen: list[dict] = []
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: seen.append(dict(e.payload)))
    ctrl.publish_goal_submit_request("New Goal", priority=1)
    assert seen and seen[0]["title"] == "New Goal"

    submitted: list[tuple[str, int]] = []
    view = GoalView(None, on_new_goal=lambda t, p: submitted.append((t, p)))
    view.apply_state(_sample_snap())
    view._hero_action.invoke()
    assert submitted == [("New Goal", 0)]


def test_goal_amber_token_used() -> None:
    files = [
        ROOT / "ai_command_center/ui/views/goal_view.py",
        ROOT / "ai_command_center/ui/views/goal_dashboard/goal_list_panel.py",
        ROOT / "ai_command_center/ui/views/goal_dashboard/goal_detail_panel.py",
        ROOT / "ai_command_center/ui/views/goal_dashboard/plan_preview_panel.py",
        ROOT / "ai_command_center/ui/views/goal_dashboard/goal_progress_panel.py",
        ROOT / "ai_command_center/ui/views/goal_dashboard/goal_history_panel.py",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "GOAL_AMBER" in text, path.name
        assert "#FFB300" not in text
    assert T.GOAL_AMBER == "#FFB300"


def test_no_repo_or_service_or_lifecycle_publishes() -> None:
    text = (ROOT / "ai_command_center/ui/views/goal_view.py").read_text(encoding="utf-8")
    assert "ai_command_center.repositories" not in text
    assert "ai_command_center.services" not in text
    assert "GOAL_ACTIVATED" not in text
    assert "GOAL_PAUSED" not in text
    assert "GOAL_CANCELLED" not in text
