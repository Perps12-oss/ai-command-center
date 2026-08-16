"""Component tests for the E04 Navigation Shell."""

from __future__ import annotations

import pytest

from ai_command_center.ui.components.keyboard_shortcuts_overlay import SHORTCUTS
from ai_command_center.ui.shell.view_manager import VIEW_IDS
from tests.ui.fake_ui import NAV_GROUPS, NavGroup, Sidebar


class _FakeMaster:
    def __init__(self) -> None:
        self._children: list[object] = []

    def winfo_width(self) -> int:
        return 200


@pytest.fixture
def sidebar():
    return Sidebar(_FakeMaster(), on_navigate=lambda v: None)


@pytest.fixture
def nav_group():
    return NavGroup(
        _FakeMaster(),
        title="Ops",
        items=[("chat", "Chat"), ("executions", "Execution Center")],
        on_select=lambda v: None,
    )


def test_view_ids_starts_with_command_center_and_has_no_home():
    assert VIEW_IDS[0] == "command_center"
    assert "home" not in VIEW_IDS


def test_workspace_nav_labels_match_ui_constitution():
    """Articles 9 / 13–16 + D5: sidebar uses canonical workspace titles."""
    labels = {vid: label for _, items in NAV_GROUPS for vid, label in items}
    assert labels["command_center"] == "Command Center"
    assert labels["executions"] == "Execution Center"
    assert labels["agents"] == "Agent Monitor"
    assert labels["approvals"] == "Approval Center"
    assert labels["goals"] == "Goal Dashboard"


def test_nav_groups_define_expected_sections():
    sections = [name for name, _ in NAV_GROUPS]
    assert sections == ["Workspace", "Knowledge", "Monitoring", "System"]
    view_ids = [vid for _, items in NAV_GROUPS for vid, _ in items]
    assert "command_center" in view_ids
    assert "workspace" in view_ids
    assert "settings" in view_ids
    assert "world_explorer" in view_ids
    assert "memory" in view_ids
    assert "timeline" in view_ids


def test_sidebar_default_active_is_command_center(sidebar):
    assert sidebar._active == "command_center"
    active_btn = sidebar._buttons["command_center"]
    assert active_btn._kwargs.get("fg_color") != "transparent"


def test_sidebar_set_active_updates_button_colors(sidebar):
    sidebar.set_active("chat")
    assert sidebar._active == "chat"
    assert sidebar._buttons["chat"]._kwargs.get("fg_color") != "transparent"
    assert sidebar._buttons["command_center"]._kwargs.get("fg_color") == "transparent"


def test_sidebar_group_toggles_update_visibility(sidebar):
    group = sidebar._groups["Workspace"]
    assert group.is_expanded
    sidebar.toggle_group("Workspace")
    assert not group.is_expanded
    sidebar.set_group_expanded("Workspace", True)
    assert group.is_expanded


def test_sidebar_badges_and_favorites(sidebar):
    sidebar.set_badge("approvals", 2)
    assert "2" in sidebar._buttons["approvals"].cget("text")
    sidebar.toggle_favorite("chat")
    assert "chat" in sidebar._prefs.favorites
    sidebar._select("goals")
    assert "goals" in sidebar._prefs.recent_pages


def test_sidebar_search_clear_restores_collapsed_groups(sidebar):
    group = sidebar._groups["Workspace"]
    sidebar._search._kwargs["text"] = "zzzz-no-match"
    sidebar._on_search()
    assert not group.is_expanded
    sidebar._search._kwargs["text"] = ""
    sidebar._on_search()
    assert group.is_expanded


def test_sidebar_compact_badges_do_not_restore_full_labels(sidebar):
    sidebar.toggle_collapse()
    assert sidebar._compact
    sidebar.set_badges({"approvals": 3, "agents": 1})
    for btn in sidebar._buttons.values():
        assert btn.cget("text") == ""
    sidebar.toggle_collapse()
    sidebar.set_badges({"approvals": 3})
    assert "Approval Center" in sidebar._buttons["approvals"].cget("text")
    assert "3" in sidebar._buttons["approvals"].cget("text")


def test_nav_group_buttons_call_on_select(nav_group):
    selected: list[str] = []
    nav_group._on_select = lambda v: selected.append(v)
    btn = nav_group.buttons["chat"]
    btn.invoke()
    assert selected == ["chat"]


def test_nav_group_toggle_changes_expanded_state(nav_group):
    assert nav_group.is_expanded
    nav_group.toggle()
    assert not nav_group.is_expanded
    nav_group.toggle()
    assert nav_group.is_expanded


def test_keyboard_shortcuts_include_navigation_category():
    categories = {group["category"] for group in SHORTCUTS}
    assert "Navigation" in categories
    nav_shortcuts = [s for g in SHORTCUTS if g["category"] == "Navigation" for s in g["shortcuts"]]
    keys = {s["keys"] for s in nav_shortcuts}
    assert "Ctrl + K" in keys
    assert "Ctrl + H" in keys
    assert "?" in keys
