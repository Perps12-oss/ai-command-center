"""UI tests for PR-UI-E13 Insights Placeholder."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_INSIGHTS_OPEN,
    UI_INSIGHTS_REFRESH,
    UI_INSIGHTS_SELECT,
)
from ai_command_center.core.state.insights_state import InsightsSnapshot
from ai_command_center.ui.components.sidebar import NAV_GROUPS
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.shell.view_manager import VIEW_IDS
from tests.ui.fake_ui import InsightsView


def test_insights_registered_in_nav_and_view_ids():
    assert "insights" in VIEW_IDS
    view_ids = [vid for _, items in NAV_GROUPS for vid, _ in items]
    assert "insights" in view_ids


def test_insights_view_shows_article18_placeholder():
    refreshed: list[str] = []
    navigated: list[str] = []
    view = InsightsView(
        None,
        on_refresh=lambda: refreshed.append("refresh"),
        on_navigate=navigated.append,
    )
    view.apply_state(AppState(insights_state=InsightsSnapshot(revision=2)))
    assert "rev 2" in view._revision.cget("text")
    banner = view._surface_state.cget("text")
    assert "Phase 10" in banner or "later Phase" in banner
    assert "Next:" in banner
    assert "No Data" not in banner
    assert "summarize" in view._detail.cget("text").lower() or "patterns" in view._detail.cget("text").lower()

    view._on_refresh()
    assert refreshed == ["refresh"]
    view._on_navigate("evidence")
    assert navigated == ["evidence"]


def test_insights_reducer_and_controller_intents():
    bus = EventBus()
    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[str] = []
    bus.subscribe(UI_INSIGHTS_OPEN, lambda e: seen.append(e.topic))
    bus.subscribe(UI_INSIGHTS_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_INSIGHTS_REFRESH, lambda e: seen.append(e.topic))

    assert store.snapshot.insights_state.status == "placeholder"
    controller.publish_insights_open()
    controller.publish_insights_select("insight-1")
    controller.publish_insights_refresh()
    assert seen == [UI_INSIGHTS_OPEN, UI_INSIGHTS_SELECT, UI_INSIGHTS_REFRESH]

    snap = store.snapshot
    assert snap.insights_state.selected_insight_id == "insight-1"
    assert snap.insights_state.revision >= 3
