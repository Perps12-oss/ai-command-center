"""C1: SystemView must not call Tk .after() from the psutil worker thread."""

from __future__ import annotations

import threading
from types import SimpleNamespace

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

from ai_command_center.ui.views import system_view as system_view_mod
from ai_command_center.ui.views.system_view import SystemView


class _RecordingQueue:
    def __init__(self) -> None:
        self.callbacks: list = []

    def enqueue(self, callback) -> None:
        self.callbacks.append(callback)


@pytest.fixture
def root():
    app = ctk.CTk()
    app.withdraw()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


def test_collect_schedules_via_ui_queue_not_after(root, monkeypatch) -> None:
    """Background _collect must enqueue UI work; never call .after() itself."""
    if not system_view_mod._PSUTIL:
        pytest.skip("psutil not installed")

    queue = _RecordingQueue()
    view = SystemView(root, ui_queue=queue)  # type: ignore[arg-type]
    view._active = True
    view._poll_generation = 1
    after_calls: list[tuple] = []

    def boom_after(*args, **kwargs):
        after_calls.append((args, kwargs))
        raise AssertionError("SystemView._collect must not call .after() from worker")

    monkeypatch.setattr(view, "after", boom_after)

    fake_vm = SimpleNamespace(percent=10.0, used=1, total=2)
    monkeypatch.setattr(
        system_view_mod._psutil,
        "cpu_percent",
        lambda interval=0: 12.0,
    )
    monkeypatch.setattr(system_view_mod._psutil, "virtual_memory", lambda: fake_vm)
    monkeypatch.setattr(
        system_view_mod._psutil,
        "Process",
        lambda: SimpleNamespace(
            memory_info=lambda: SimpleNamespace(rss=1024 * 1024),
            cpu_percent=lambda interval=0: 1.0,
        ),
    )
    monkeypatch.setattr(system_view_mod._psutil, "process_iter", lambda attrs: [])
    monkeypatch.setattr(system_view_mod._psutil, "disk_io_counters", lambda: None)
    monkeypatch.setattr(system_view_mod._psutil, "net_io_counters", lambda: None)

    view._collect(1)

    assert after_calls == []
    assert len(queue.callbacks) >= 1
    # First enqueue is UI update; last schedules the delayed re-poll on the UI thread.
    assert any(callable(cb) for cb in queue.callbacks)


def test_collect_from_worker_thread_never_touches_after(root, monkeypatch) -> None:
    if not system_view_mod._PSUTIL:
        pytest.skip("psutil not installed")

    queue = _RecordingQueue()
    view = SystemView(root, ui_queue=queue)  # type: ignore[arg-type]
    view._active = True
    view._poll_generation = 7
    after_calls: list = []
    monkeypatch.setattr(
        view,
        "after",
        lambda *a, **k: after_calls.append((threading.current_thread().name, a)),
    )
    monkeypatch.setattr(system_view_mod._psutil, "cpu_percent", lambda interval=0: 1.0)
    monkeypatch.setattr(
        system_view_mod._psutil,
        "virtual_memory",
        lambda: SimpleNamespace(percent=1.0, used=1, total=2),
    )
    monkeypatch.setattr(
        system_view_mod._psutil,
        "Process",
        lambda: SimpleNamespace(
            memory_info=lambda: SimpleNamespace(rss=1024),
            cpu_percent=lambda interval=0: 0.0,
        ),
    )
    monkeypatch.setattr(system_view_mod._psutil, "process_iter", lambda attrs: [])
    monkeypatch.setattr(system_view_mod._psutil, "disk_io_counters", lambda: None)
    monkeypatch.setattr(system_view_mod._psutil, "net_io_counters", lambda: None)

    done = threading.Event()
    err: list[BaseException] = []

    def worker() -> None:
        try:
            view._collect(7)
        except BaseException as exc:  # noqa: BLE001 — surface to test thread
            err.append(exc)
        finally:
            done.set()

    thread = threading.Thread(target=worker, name="system-view-collect-test")
    thread.start()
    assert done.wait(timeout=5.0)
    thread.join(timeout=2.0)
    assert err == []
    assert after_calls == []
    assert queue.callbacks


def test_schedule_on_ui_uses_queue(root) -> None:
    queue = _RecordingQueue()
    view = SystemView(root, ui_queue=queue)  # type: ignore[arg-type]
    seen: list[int] = []
    view._schedule_on_ui(lambda: seen.append(1))
    assert len(queue.callbacks) == 1
    queue.callbacks[0]()
    assert seen == [1]
