"""Program 1 S5 — state store and UI lifecycle teardown tests."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_command_center.application import create_application
from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import SETTINGS_SNAPSHOT, TOOL_INVOKE
from ai_command_center.db.connection import connect, init_database

_WIN_TK = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only Tkinter UI")


def _ctk_root_or_skip():
    """Create a withdrawn CTk root; skip when Tk assets are unavailable."""
    pytest.importorskip("customtkinter")
    import customtkinter as ctk

    try:
        root = ctk.CTk()
    except Exception as exc:  # noqa: BLE001 — TclError varies by platform
        pytest.skip(f"Tk unavailable in this environment: {exc}")
    root.withdraw()
    return root


def test_application_shutdown_closes_state_store() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db, workspace_os_enabled=False)
    core.startup()
    assert core.state_store._unsubscribers, "AppState should subscribe to bus topics"
    core.shutdown()
    assert core.state_store._unsubscribers == []


def test_application_shutdown_stops_bus_before_db_close() -> None:
    order: list[str] = []

    class _Bus:
        dispatch_queue_depth = 0

        def publish(self, *_args, **_kwargs):
            order.append("publish")
            class _Event:
                delivery = "delivered"
            return _Event()

        def shutdown(self, **_kwargs):
            order.append("bus.shutdown")

    class _Services:
        def shutdown(self):
            order.append("services.shutdown")

    class _State:
        def close(self):
            order.append("state.close")

    class _DB:
        in_transaction = False

        def close(self):
            order.append("db.close")

    from ai_command_center.application import ApplicationCore

    core = ApplicationCore(
        bus=_Bus(),  # type: ignore[arg-type]
        state_store=_State(),  # type: ignore[arg-type]
        services=_Services(),  # type: ignore[arg-type]
        db=_DB(),  # type: ignore[arg-type]
    )
    core.shutdown()
    assert order == [
        "services.shutdown",
        "state.close",
        "publish",
        "bus.shutdown",
        "db.close",
    ]


def test_application_tool_invoke_dispatch_does_not_block_publisher() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db, workspace_os_enabled=False)
    release = threading.Event()
    handled = threading.Event()

    def slow_handler(_event) -> None:
        release.wait(timeout=2.0)
        handled.set()

    core.bus.subscribe(TOOL_INVOKE, slow_handler)
    started = time.perf_counter()
    try:
        core.bus.publish(TOOL_INVOKE, {"tool": "shell"}, source="test")
        elapsed = time.perf_counter() - started
        assert elapsed < 0.25
        assert not handled.is_set()
        release.set()
        assert handled.wait(timeout=2.0)
    finally:
        release.set()
        core.shutdown()


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
def test_system_view_does_not_sample_psutil(monkeypatch) -> None:
    """UI isolation — SystemView projects snapshots; it must not call psutil."""
    from ai_command_center.domain.system_snapshot import SystemSnapshot
    from ai_command_center.ui.views.system_view import SystemView

    root = _ctk_root_or_skip()
    try:
        view = SystemView(root)
        view.on_show()
        view.apply_system_snapshot(
            SystemSnapshot(
                cpu_percent=12.0,
                ram_percent=34.0,
                extra={
                    "proc_mem_mb": 100.0,
                    "proc_cpu": 1.0,
                    "top_processes": [{"pid": 1, "cpu": 1.0, "mem": 0.5, "name": "init"}],
                    "disk_read_bps": 10.0,
                    "disk_write_bps": 20.0,
                    "net_recv_bps": 30.0,
                    "net_sent_bps": 40.0,
                },
            )
        )
        assert view._active is True
        view.on_hide()
        assert view._active is False
    finally:
        root.destroy()


@_WIN_TK
def test_system_view_on_hide_clears_active() -> None:
    from ai_command_center.ui.views.system_view import SystemView

    root = _ctk_root_or_skip()
    try:
        view = SystemView(root)
        view.on_show()
        assert view._active is True
        view.on_hide()
        assert view._active is False
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
