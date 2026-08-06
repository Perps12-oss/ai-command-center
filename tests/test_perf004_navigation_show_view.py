"""PERF-004 — navigation show_view / sidebar dirty-update contracts (headless)."""

from __future__ import annotations

from tests.ui.fake_ui import Sidebar


class _CountingMaster:
    def __init__(self) -> None:
        self._children: list[object] = []

    def winfo_width(self) -> int:
        return 200


def _wrap_configure_counters(sidebar: Sidebar) -> list[str]:
    """Instrument button.configure to record which view_ids were touched."""
    touched: list[str] = []
    for vid, btn in sidebar._buttons.items():
        original = btn.configure

        def _make(view_id: str, orig):
            def _wrapped(**kwargs):
                touched.append(view_id)
                return orig(**kwargs)

            return _wrapped

        btn.configure = _make(vid, original)  # type: ignore[method-assign]
    return touched


def test_sidebar_set_active_dirty_badge_configures_two_not_all() -> None:
    """PERF-004: A→B badge/active label updates must not reconfigure all 26."""
    sidebar = Sidebar(_CountingMaster(), on_navigate=lambda _v: None)
    n = len(sidebar._buttons)
    assert n >= 20
    touched = _wrap_configure_counters(sidebar)
    touched.clear()
    sidebar.set_active("chat")
    # Dirty: previous (command_center) + new (chat) for badge texts,
    # plus NavGroup color configures on those buttons (same ids).
    assert len(touched) <= 6, touched
    assert "chat" in touched
    assert "command_center" in touched
    # Must not touch unrelated nav items (e.g. settings).
    assert "settings" not in touched


def test_sidebar_set_active_same_view_is_noop() -> None:
    sidebar = Sidebar(_CountingMaster(), on_navigate=lambda _v: None)
    sidebar.set_active("chat")
    touched = _wrap_configure_counters(sidebar)
    touched.clear()
    sidebar.set_active("chat")
    assert touched == []


def test_show_view_same_id_skips_pack_forget() -> None:
    """PERF-004: _show_view early-out must not pack_forget when already showing."""
    pack_forgets: list[str] = []

    class _View:
        def __init__(self, name: str) -> None:
            self.name = name

        def pack_forget(self) -> None:
            pack_forgets.append(self.name)

        def pack(self, **_kwargs) -> None:
            pass

        def on_show(self) -> None:
            pass

        def on_hide(self) -> None:
            pass

    class _Sidebar:
        _active = "chat"

        def set_active(self, view_id: str) -> None:
            self._active = view_id

    class _Shell:
        VIEW_IDS = ("command_center", "chat", "settings")

        def __init__(self) -> None:
            self._current_view = "chat"
            self._views = {"chat": _View("chat"), "settings": _View("settings")}
            self._sidebar = _Sidebar()

        def _ensure_view(self, view_id: str):
            return self._views[view_id]

        def _chat_view(self):
            return None

    from ai_command_center.ui.shell.view_manager import ViewManagerMixin

    shell = _Shell()
    pack_forgets.clear()
    ViewManagerMixin._show_view(shell, "chat")  # type: ignore[arg-type]
    assert pack_forgets == []


def test_show_view_switch_pack_forgets_only_previous() -> None:
    from ai_command_center.ui.shell.view_manager import ViewManagerMixin

    pack_forgets: list[str] = []

    class _View:
        def __init__(self, name: str) -> None:
            self.name = name

        def pack_forget(self) -> None:
            pack_forgets.append(self.name)

        def pack(self, **_kwargs) -> None:
            pass

        def on_show(self) -> None:
            pass

        def on_hide(self) -> None:
            pass

    class _Sidebar:
        _active = "command_center"

        def set_active(self, view_id: str) -> None:
            self._active = view_id

    class _Shell:
        def __init__(self) -> None:
            self._current_view = "command_center"
            self._views = {
                "command_center": _View("command_center"),
                "chat": _View("chat"),
                "settings": _View("settings"),
            }
            self._sidebar = _Sidebar()

        def _ensure_view(self, view_id: str):
            return self._views[view_id]

        def _chat_view(self):
            return None

    shell = _Shell()
    pack_forgets.clear()
    ViewManagerMixin._show_view(shell, "chat")  # type: ignore[arg-type]
    assert pack_forgets == ["command_center"]
    assert shell._current_view == "chat"
