"""Goal Dashboard EventBus publication path tests (GOAL_SUBMIT_REQUEST only)."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    GOAL_ACTIVATED,
    GOAL_CANCELLED,
    GOAL_PAUSED,
    GOAL_SUBMIT_REQUEST,
)
from ai_command_center.domain.brain_state_snapshot import BrainStateSnapshot, GoalSnapshot
from ai_command_center.ui.controller import UIController
from tests.ui.fake_ui import GoalView


def test_view_manager_style_new_goal_path_publishes_submit_only() -> None:
    """Mirrors ViewManager._on_goal_new → UIController.publish_goal_submit_request."""
    bus = EventBus()
    store = AppStateStore(bus)
    ctrl = UIController(bus, store, on_state=lambda: None)
    submitted: list[dict] = []
    lifecycle: list[str] = []
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: submitted.append(dict(e.payload)))
    for topic in (GOAL_ACTIVATED, GOAL_PAUSED, GOAL_CANCELLED):
        bus.subscribe(topic, lambda e, t=topic: lifecycle.append(t))

    def on_new_goal(title: str, priority: int = 0) -> None:
        ctrl.publish_goal_submit_request(title, priority=priority)

    view = GoalView(None, on_new_goal=on_new_goal)
    view.apply_state(
        AppState(
            brain_state=BrainStateSnapshot(
                recent_goals=(
                    GoalSnapshot(goal_id="g1", text="Ship", status="active", priority=1),
                )
            )
        )
    )
    view._hero_action.invoke()

    assert len(submitted) == 1
    assert submitted[0]["title"] == "New Goal"
    assert submitted[0]["priority"] == 0
    assert lifecycle == []


def test_controller_payload_includes_goal_aliases() -> None:
    bus = EventBus()
    ctrl = UIController(bus, AppStateStore(bus), on_state=lambda: None)
    seen: list[dict] = []
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: seen.append(dict(e.payload)))
    ctrl.publish_goal_submit_request(
        "Investigate outage",
        priority=2,
        description="sev-1",
        goal_id="g-42",
    )
    assert seen[0]["title"] == "Investigate outage"
    assert seen[0]["goal"] == "Investigate outage"
    assert seen[0]["priority"] == 2
    assert seen[0]["description"] == "sev-1"
    assert seen[0]["goal_id"] == "g-42"
