"""Program 1 S5 — state store and UI lifecycle teardown tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_command_center.application import create_application
from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import SETTINGS_SNAPSHOT
from ai_command_center.db.connection import connect, init_database

_WIN_TK = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only Tkinter UI")


def test_application_shutdown_closes_state_store() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db, workspace_os_enabled=False)
    core.startup()
    assert core.state_store._unsubscribers, "AppState should subscribe to bus topics"
    core.shutdown()
    assert core.state_store._unsubscribers == []


def test_app_state_close_clears_bus_subscriptions() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    revisions: list[int] = []

    def listener(_state) -> None:
        revisions.append(1)

    store.subscribe(listener)
    bus.publish(SETTINGS_SNAPSHOT, {"theme": "dark"}, source="test")
    assert store.snapshot.settings.theme == "dark"

    store.close()
    bus.publish(SETTINGS_SNAPSHOT, {"theme": "light"}, source="test")
    assert store.snapshot.settings.theme == "dark"
    assert revisions == [1]


@_WIN_TK
def test_command_palette_destroy_unsubscribes_bus() -> None:
    pytest.importorskip("customtkinter")
    from ai_command_center.ui.app import CommandPaletteApp

    bus = EventBus()
    store = AppStateStore(bus)
    app = CommandPaletteApp(bus, store, workspace_os_enabled=False)
    assert app._bus_unsubs, "shell should subscribe to bus topics"
    app.destroy()
    assert app._bus_unsubs == []


def test_eventbus_topic_counts_in_system_snapshot() -> None:
    """S6 — topic publish counters surface in system.snapshot payloads."""
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.core.events.topics import SETTINGS_SNAPSHOT, SYSTEM_SNAPSHOT
    from ai_command_center.services.system_monitor_service import SystemMonitorService

    bus = EventBus()
    bus.publish(SETTINGS_SNAPSHOT, {"theme": "dark"}, source="test")
    bus.publish(SETTINGS_SNAPSHOT, {"theme": "light"}, source="test")

    snapshots: list[dict] = []
    bus.subscribe(SYSTEM_SNAPSHOT, lambda e: snapshots.append(dict(e.payload)))

    service = SystemMonitorService(bus)
    service.start()
    try:
        # Payload counts are sampled before the current publish increments.
        service._publish_snapshot()
        service._publish_snapshot()
        assert snapshots, "expected a system.snapshot publish"
        counts = snapshots[-1].get("eventbus_topic_counts")
        assert isinstance(counts, dict)
        assert counts.get(SETTINGS_SNAPSHOT, 0) >= 2
        assert counts.get(SYSTEM_SNAPSHOT, 0) >= 1
    finally:
        service.stop()


@_WIN_TK
def test_system_view_on_hide_stops_psutil_activity(monkeypatch) -> None:
    """S4 — after on_hide(), psutil collection must not continue."""
    pytest.importorskip("customtkinter")
    import customtkinter as ctk

    from ai_command_center.ui.views import system_view as sv_mod
    from ai_command_center.ui.views.system_view import SystemView

    if not sv_mod._PSUTIL:
        pytest.skip("psutil not available")

    monkeypatch.setattr(SystemView, "_POLL_MS", 50)

    psutil_calls = {"n": 0}

    class _VM:
        percent = 10.0
        used = 1
        total = 8

    class _Proc:
        def memory_info(self):
            class _Mem:
                rss = 50 * 1024 * 1024

            return _Mem()

        def cpu_percent(self, interval=0):
            return 1.0

    def _bump_cpu(*_args, **_kwargs):
        psutil_calls["n"] += 1
        return 5.0

    monkeypatch.setattr(sv_mod._psutil, "cpu_percent", _bump_cpu)
    monkeypatch.setattr(sv_mod._psutil, "virtual_memory", lambda: _VM())
    monkeypatch.setattr(sv_mod._psutil, "Process", _Proc)
    monkeypatch.setattr(sv_mod._psutil, "process_iter", lambda *_a, **_k: iter([]))
    monkeypatch.setattr(sv_mod._psutil, "disk_io_counters", lambda: None)
    monkeypatch.setattr(sv_mod._psutil, "net_io_counters", lambda: None)

    root = ctk.CTk()
    root.withdraw()
    try:
        view = SystemView(root)
        view.on_show()
        for _ in range(40):
            root.update()
            if psutil_calls["n"] > 0:
                break
            root.after(25)
        assert psutil_calls["n"] > 0, "expected psutil activity while visible"

        view.on_hide()
        count_at_hide = psutil_calls["n"]

        for _ in range(40):
            root.update()
            root.after(25)

        assert psutil_calls["n"] == count_at_hide, (
            f"psutil kept running after on_hide: {psutil_calls['n']} vs {count_at_hide}"
        )
        assert view._active is False
    finally:
        root.destroy()


@_WIN_TK
def test_system_view_on_hide_stops_poll_generation() -> None:
    pytest.importorskip("customtkinter")
    import customtkinter as ctk

    from ai_command_center.ui.views.system_view import SystemView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = SystemView(root)
        gen_before = view._poll_generation
        view.on_show()
        assert view._active is True
        view.on_hide()
        assert view._active is False
        assert view._poll_generation > gen_before
    finally:
        root.destroy()


def test_tool_executor_unload_cancels_shell(monkeypatch) -> None:
    from ai_command_center.services import tool_executor_service as tes
    from ai_command_center.tools.tool_registry import ToolRegistry

    killed = MagicMock(return_value=True)
    monkeypatch.setattr(tes, "cancel_active_shell", killed)

    bus = EventBus()
    service = tes.ToolExecutorService(bus, ToolRegistry())
    service.start()
    service.stop()
    killed.assert_called_once()
