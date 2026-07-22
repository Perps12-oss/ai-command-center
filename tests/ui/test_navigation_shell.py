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


def test_nav_groups_define_expected_sections():
    sections = [name for name, _ in NAV_GROUPS]
    assert sections == ["Workspaces", "Ops", "Monitor", "Library", "Settings"]
    view_ids = [vid for _, items in NAV_GROUPS for vid, _ in items]
    assert "command_center" in view_ids
    assert "workspace" in view_ids
    assert "settings" in view_ids


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
    group = sidebar._groups["Ops"]
    assert group.is_expanded
    sidebar.toggle_group("Ops")
    assert not group.is_expanded
    sidebar.set_group_expanded("Ops", True)
    assert group.is_expanded


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
