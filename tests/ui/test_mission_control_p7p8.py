"""P7–P8 Mission Control completion tests."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    GOAL_CANCEL_REQUEST,
    GOAL_PAUSE_REQUEST,
    GOAL_RESUME_REQUEST,
    PERMISSION_CHECK_RESULT,
)
from ai_command_center.core.app_state import AppState
from ai_command_center.domain.brain_state_snapshot import (
    BrainStateSnapshot,
    GoalSnapshot as BrainGoalSnapshot,
)
from ai_command_center.domain.execution_library_snapshot import (
    ExecutionLibrarySnapshot,
    ExecutionPlanSnapshot,
)
from ai_command_center.domain.permission_check_snapshot import (
    PendingCheck,
    PermissionCheckSnapshot,
)
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.design_system import theme_manager
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.mission_control.layout_prefs import Density, LayoutPrefs
from ai_command_center.ui.tray import TrayController
from tests.ui.fake_ui import CommandCenterView


def test_layout_prefs_round_trip_and_reorder() -> None:
    prefs = LayoutPrefs(density=Density.COMPACT, favorites=["chat"], show_advanced=True)
    prefs.move_widget("mid", 1)
    raw = prefs.to_dict()
    restored = LayoutPrefs.from_dict(raw)
    assert restored.density == Density.COMPACT
    assert restored.favorites == ["chat"]
    assert restored.show_advanced is True
    assert "mid" in restored.widget_order


def test_theme_manager_applies_light_and_high_contrast() -> None:
    class _Win:
        def __init__(self) -> None:
            self.alpha = None
            self.fg = None

        def attributes(self, key, value=None):
            if key == "-alpha" and value is not None:
                self.alpha = value

        def configure(self, **kwargs):
            self.fg = kwargs.get("fg_color")

    win = _Win()
    theme_manager.apply(win, theme_name="Light")
    assert theme_manager.active_name() == "Light"
    assert T.BG_DEEP == T.LIGHT_THEME_BG or T.BG_DEEP == "#F5F7FA"
    theme_manager.apply(win, theme_name="High Contrast")
    assert theme_manager.active_name() == "High Contrast"
    assert T.TEXT_PRIMARY == T.HIGH_CONTRAST_TEXT or T.TEXT_PRIMARY == "#FFFFFF"
    # Restore a dark theme for other tests
    theme_manager.apply(win, theme_name="VS Dark")


def test_goal_control_request_topics() -> None:
    bus = EventBus()
    store = __import__(
        "ai_command_center.core.app_state", fromlist=["AppStateStore"]
    ).AppStateStore(bus)
    ctrl = UIController(bus, store, on_state=lambda _s: None)
    seen: list[tuple[str, dict]] = []

    def capture(event) -> None:
        seen.append((event.topic, dict(event.payload)))

    bus.subscribe(GOAL_PAUSE_REQUEST, capture)
    bus.subscribe(GOAL_RESUME_REQUEST, capture)
    bus.subscribe(GOAL_CANCEL_REQUEST, capture)
    ctrl.publish_goal_pause_request("g1")
    ctrl.publish_goal_resume_request("g1")
    ctrl.publish_goal_cancel_request("g1", reason="aborted")
    topics = [t for t, _ in seen]
    assert GOAL_PAUSE_REQUEST in topics
    assert GOAL_RESUME_REQUEST in topics
    assert GOAL_CANCEL_REQUEST in topics


def test_hero_waiting_approve_publishes_permission_result() -> None:
    bus = EventBus()
    store = __import__(
        "ai_command_center.core.app_state", fromlist=["AppStateStore"]
    ).AppStateStore(bus)
    # Direct view-level approve callback simulation
    published: list[dict] = []

    def on_approve() -> None:
        bus.publish(
            PERMISSION_CHECK_RESULT,
            {
                "check_id": "c1",
                "granted": True,
                "permissions": ["read"],
                "actor_type": "agent",
                "actor_id": "a1",
            },
            source="ui",
        )

    bus.subscribe(PERMISSION_CHECK_RESULT, lambda e: published.append(dict(e.payload)))
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
        on_approve=on_approve,
    )
    snap = AppState(
        brain_state=BrainStateSnapshot(
            recent_goals=(BrainGoalSnapshot(goal_id="g1", text="Ship", status="active"),),
        ),
        permission_snapshot=PermissionCheckSnapshot(
            pending=PendingCheck(
                check_id="c1",
                permissions=("read",),
                actor_id="a1",
                summary="Allow?",
            ),
        ),
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="running", total_steps=2),
        ),
    )
    view.apply_state(snap)
    assert view._hero_panel._primary_kind == "approve"
    view._action_button.invoke()
    assert published and published[0]["granted"] is True


def test_hero_pause_secondary_kind() -> None:
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
        on_pause_goal=lambda _gid: None,
    )
    snap = AppState(
        brain_state=BrainStateSnapshot(
            recent_goals=(BrainGoalSnapshot(goal_id="g9", text="Run", status="active"),),
        ),
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="running", total_steps=3),
        ),
    )
    view.apply_state(snap)
    assert view._hero_panel._secondary_kind == "pause"
    assert view._hero_panel._secondary_button.cget("text") == "Pause"


def test_tray_tooltip_includes_queue_and_providers() -> None:
    tray = TrayController(
        on_open=lambda: None,
        on_exit=lambda: None,
        get_phase=lambda: "idle",
        get_status=lambda: {
            "queue": 2,
            "providers_healthy": 3,
            "providers_total": 4,
            "pending_approvals": 1,
            "ollama_online": True,
        },
    )
    tip = tray._tooltip()
    assert "Queue 2" in tip
    assert "Providers 3/4" in tip
    assert "Approvals 1" in tip
    assert tray._effective_phase() == "busy"
