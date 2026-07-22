"""UI tests for PR-UI-E06 Brain Inspector."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_BRAIN_OPEN, UI_BRAIN_SELECT
from ai_command_center.domain.brain_state_snapshot import (
    BrainStateSnapshot,
    GoalSnapshot,
    ObservationSnapshot,
    PlanSnapshot,
    PlanStepSnapshot,
    RuntimeActionSnapshot,
)
from ai_command_center.ui.components.sidebar import NAV_GROUPS
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.shell.view_manager import VIEW_IDS
from tests.ui.fake_ui import BrainView, GoalCard, PlanCard


def test_brain_registered_in_nav_and_view_ids():
    assert "brain" in VIEW_IDS
    view_ids = [vid for _, items in NAV_GROUPS for vid, _ in items]
    assert "brain" in view_ids


def test_brain_view_projects_snapshot():
    inspected: list[object] = []
    view = BrainView(None, on_inspect_select=lambda ref: inspected.append(ref))
    snap = AppState(
        brain_state=BrainStateSnapshot(
            kernel_state="ready",
            recent_goals=(GoalSnapshot(goal_id="g1", text="Ship E06", status="active"),),
            recent_observations=(
                ObservationSnapshot(observation_id="o1", content="saw merge", source="git"),
            ),
            recent_runtime_actions=(
                RuntimeActionSnapshot(action_id="a1", action_type="test", status="ok"),
            ),
            last_plan=PlanSnapshot(
                plan_id="p1",
                goal="Ship E06",
                status="active",
                steps=(PlanStepSnapshot(step_id="s1", description="implement", status="done"),),
            ),
        )
    )
    view.apply_state(snap)
    assert "ready" in view._kernel_lbl.cget("text")
    assert "Ship E06" in view._hint.cget("text")
    view._select_goal("g1")
    assert inspected and getattr(inspected[0], "kind") == "goal"


def test_goal_and_plan_cards():
    selected: list[str] = []
    GoalCard(
        None,
        goal_id="g1",
        text="T",
        status="active",
        on_select=lambda gid: selected.append(gid),
    )._click()
    assert selected == ["g1"]
    PlanCard(None, plan_id="p1", goal="G", status="active", steps=(("step", "done"),))


def test_controller_brain_intents():
    bus = EventBus()
    from ai_command_center.core.app_state import AppStateStore

    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[str] = []
    bus.subscribe(UI_BRAIN_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_BRAIN_OPEN, lambda e: seen.append(e.topic))
    controller.publish_brain_select("g1")
    controller.publish_brain_open()
    assert seen == [UI_BRAIN_SELECT, UI_BRAIN_OPEN]
