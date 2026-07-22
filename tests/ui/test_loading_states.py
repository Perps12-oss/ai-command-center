"""Article 18 loading / empty surface-state tests for Phase 11 workspaces."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.brain_state_snapshot import BrainStateSnapshot
from ai_command_center.ui.views.surface_state import article18_empty, article18_loading
from tests.ui.fake_ui import (
    AgentsView,
    ApprovalsView,
    CommandCenterView,
    EvidenceView,
    ExecutionsView,
    GoalView,
    WorldExplorerView,
)


def _assert_loading_banner(text: str) -> None:
    assert "Status:" in text
    assert "Loading:" in text
    assert "Next:" in text
    assert "No Data" not in text


def test_article18_helpers_format() -> None:
    loading = article18_loading(
        status="Status: loading X",
        what="projection Y",
        next_action="Wait",
    )
    assert loading.splitlines() == [
        "Status: loading X",
        "Loading: projection Y",
        "Next: Wait",
    ]
    empty = article18_empty(why="Why", creates="Creates", next_action="Do this")
    assert "Why" in empty and "Creates" in empty and "Next: Do this" in empty


def test_all_phase11_shells_show_structured_loading_on_none() -> None:
    shells = (
        CommandCenterView(None),
        WorldExplorerView(None),
        ExecutionsView(None),
        EvidenceView(None),
        AgentsView(None),
        ApprovalsView(None),
        GoalView(None),
    )
    for view in shells:
        view.apply_state(None)
        _assert_loading_banner(view._surface_state.cget("text"))


def test_command_center_and_goal_empty_states() -> None:
    cc = CommandCenterView(None)
    cc.apply_state(AppState(brain_state=BrainStateSnapshot()))
    surface = cc._surface_state.cget("text")
    assert "Next:" in surface
    assert "No Data" not in surface

    goals = GoalView(None)
    goals.apply_state(AppState(brain_state=BrainStateSnapshot()))
    g_surface = goals._surface_state.cget("text")
    assert "Next:" in g_surface
    assert "No Data" not in g_surface


def test_execution_hero_disabled_when_empty() -> None:
    view = ExecutionsView(None)
    view.apply_state(AppState())
    assert view._hero_action.cget("state") == "disabled"
    assert "No Executions" in view._hero_action.cget("text")
    assert "Next:" in view._surface_state.cget("text")
