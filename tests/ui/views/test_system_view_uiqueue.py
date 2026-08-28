"""SystemView projects SystemSnapshot; it must not call psutil."""

from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _probe = tk.Tk()
    _probe.withdraw()
    _probe.destroy()
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

import customtkinter as ctk

from ai_command_center.domain.system_snapshot import SystemSnapshot
from ai_command_center.ui.views import system_view as system_view_mod
from ai_command_center.ui.views.system_view import SystemView


@pytest.fixture
def root():
    app = ctk.CTk()
    app.withdraw()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


def test_system_view_has_no_psutil_collector(root) -> None:
    view = SystemView(root)
    assert not hasattr(view, "_collect")
    assert not hasattr(system_view_mod, "_psutil")


def test_apply_system_snapshot_updates_meters(root) -> None:
    view = SystemView(root)
    view.apply_system_snapshot(
        SystemSnapshot(
            cpu_percent=22.0,
            ram_percent=44.0,
            extra={
                "proc_mem_mb": 12.0,
                "top_processes": [{"pid": 2, "cpu": 3.0, "mem": 1.0, "name": "x"}],
                "disk_read_bps": 1.0,
                "disk_write_bps": 2.0,
                "net_recv_bps": 3.0,
                "net_sent_bps": 4.0,
            },
        )
    )
    assert "SystemSnapshot" in view._proc_lbl.cget("text")
