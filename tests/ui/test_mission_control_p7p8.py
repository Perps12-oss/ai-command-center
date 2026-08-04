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


def test_hero_waiting_review_approval_navigates_not_auto_grant() -> None:
    """Review Approval must open Approvals — never grant from the hero."""
    navigated: list[str] = []
    published: list[dict] = []

    bus = EventBus()
    bus.subscribe(PERMISSION_CHECK_RESULT, lambda e: published.append(dict(e.payload)))

    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda vid: navigated.append(vid),
        on_approve=lambda: navigated.append("approvals"),
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
    assert navigated == ["approvals"]
    assert published == []


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


def test_record_page_does_not_persist_immediately() -> None:
    writes: list[dict] = []
    prefs = LayoutPrefs()
    prefs.bind_persist(lambda p: writes.append(p.to_dict()))
    prefs.record_page("chat")
    prefs.record_page("goals")
    assert prefs.recent_pages[0] == "goals"
    assert writes == []
    assert prefs._dirty is True
    prefs.flush()
    assert writes and writes[0]["recent_pages"][0] == "goals"
    assert prefs._dirty is False


def test_record_page_debounce_callback_scheduled() -> None:
    writes: list[dict] = []
    scheduled: list[LayoutPrefs] = []
    prefs = LayoutPrefs()
    prefs.bind_persist(
        lambda p: writes.append(p.to_dict()),
        on_debounce=lambda p: scheduled.append(p),
    )
    prefs.record_page("brain")
    assert scheduled and scheduled[0] is prefs
    assert writes == []
    # Favorites still persist immediately
    prefs.toggle_favorite("chat")
    assert writes and "chat" in writes[-1]["favorites"]


def test_hero_ignores_finished_goal_for_control_ids() -> None:
    aborted: list[str] = []
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
        on_abort_goal=lambda gid: aborted.append(gid),
    )
    snap = AppState(
        brain_state=BrainStateSnapshot(
            recent_goals=(
                BrainGoalSnapshot(goal_id="old", text="Done mission", status="completed"),
            ),
        ),
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="failed", error="boom", total_steps=1),
        ),
    )
    view.apply_state(snap)
    hero = view._hero_panel
    assert hero._active_goal_id == ""
    assert hero._abort_goal_id == ""
    assert hero._secondary_kind != "abort"


def test_hero_resume_uses_paused_goal_id() -> None:
    resumed: list[str] = []
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
        on_resume_goal=lambda gid: resumed.append(gid),
        on_pause_goal=lambda _gid: None,
    )
    snap = AppState(
        brain_state=BrainStateSnapshot(
            recent_goals=(
                BrainGoalSnapshot(goal_id="active-1", text="Live", status="active"),
                BrainGoalSnapshot(goal_id="paused-1", text="Paused", status="paused"),
            ),
        ),
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="running", total_steps=2),
        ),
    )
    view.apply_state(snap)
    hero = view._hero_panel
    assert hero._active_goal_id == "active-1"
    assert hero._paused_goal_id == "paused-1"
    # Force resume path
    hero._primary_kind = "resume"
    hero._on_action()
    assert resumed == ["paused-1"]


def test_exec_dock_shows_most_recent_events() -> None:
    from ai_command_center.core.state.execution_timeline_state import ExecutionTimelineState
    from ai_command_center.domain.execution_event import ExecutionEvent

    events = tuple(
        ExecutionEvent(
            event_id=f"e{i}",
            trace_id="t1",
            parent_event_id=None,
            timestamp=float(i),
            event_type=f"step_{i}",
            actor="system",
            scope="execution",
            request_id="r1",
        )
        for i in range(30)
    )
    view = CommandCenterView(None, on_command=lambda _x: None, on_navigate=lambda _x: None)
    snap = AppState(execution_timeline=ExecutionTimelineState(events=events, revision=1))
    view.apply_state(snap)
    steps = view._exec_dock._steps
    assert len(steps) == 24
    assert steps[0]["name"] == "step 6"
    assert steps[-1]["name"] == "step 29"


def test_exec_dock_fallback_recent_events_are_newest_first() -> None:
    """recent_execution_events is newest-first; dock must still show the latest window."""
    from ai_command_center.core.state.execution_event_state import ExecutionEventItem

    # Newest-first catalog (index 0 = newest), as AppState maintains it.
    recent = tuple(
        ExecutionEventItem(
            event_id=f"e{i}",
            timestamp=float(i),
            event_type=f"step_{i}",
            request_id="r1",
        )
        for i in range(29, -1, -1)
    )
    view = CommandCenterView(None, on_command=lambda _x: None, on_navigate=lambda _x: None)
    view.apply_state(AppState(recent_execution_events=recent))
    steps = view._exec_dock._steps
    assert len(steps) == 24
    assert steps[0]["name"] == "step 6"
    assert steps[-1]["name"] == "step 29"


def test_exec_dock_scrub_publishes_global_index_with_offset() -> None:
    from ai_command_center.core.state.execution_timeline_state import ExecutionTimelineState
    from ai_command_center.domain.execution_event import ExecutionEvent

    scrubbed: list[int] = []
    events = tuple(
        ExecutionEvent(
            event_id=f"e{i}",
            trace_id="t1",
            parent_event_id=None,
            timestamp=float(i),
            event_type=f"step_{i}",
            actor="system",
            scope="execution",
            request_id="r1",
        )
        for i in range(30)
    )
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
        on_scrub=scrubbed.append,
    )
    view.apply_state(AppState(execution_timeline=ExecutionTimelineState(events=events, revision=1)))
    assert view._exec_window_offset == 6
    # Local index 0 in the visible window → global index 6
    view._handle_exec_scrub(0)
    assert scrubbed == [6]
    view._handle_exec_scrub(23)
    assert scrubbed[-1] == 29


def test_tray_refresh_updates_title() -> None:
    status = {"queue": 0, "providers_healthy": 1, "providers_total": 1, "pending_approvals": 0, "ollama_online": False}

    tray = TrayController(
        on_open=lambda: None,
        on_exit=lambda: None,
        get_phase=lambda: "idle",
        get_status=lambda: dict(status),
    )

    class _Icon:
        def __init__(self) -> None:
            self.icon = None
            self.title = "initial"

    tray._icon = _Icon()
    tray.refresh()
    assert "Queue 0" in tray._icon.title
    status["queue"] = 5
    status["pending_approvals"] = 2
    tray.refresh()
    assert "Queue 5" in tray._icon.title
    assert "Approvals 2" in tray._icon.title

