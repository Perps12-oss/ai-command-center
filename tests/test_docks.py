"""Dock component smoke tests."""

from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _root = tk.Tk()
    _root.withdraw()
    _root.destroy()
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.docks import ExecutionTimelineDock, InspectorDock
from ai_command_center.ui.components.inspector import MessageInspector


def test_inspector_dock_hosts_inspector() -> None:
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:
        pytest.skip(f"tkinter display unavailable: {exc}")
    try:
        dock = InspectorDock(root)
        dock.pack(fill="both", expand=True)
        dock.register("message", MessageInspector(dock.host))

        ref = InspectableRef.from_payload(
            {
                "kind": "message",
                "ref_id": "msg-1",
                "label": "Docked message",
                "payload": {"role": "user", "content": "hello"},
            }
        )
        dock.show(ref)
        root.update_idletasks()
        assert dock.host._title.cget("text") == "Docked message"
    finally:
        root.destroy()


def test_execution_timeline_dock_renders_and_scrubs() -> None:
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:
        pytest.skip(f"tkinter display unavailable: {exc}")
    scrubbed: list[int] = []
    try:
        dock = ExecutionTimelineDock(root, on_scrub=scrubbed.append)
        dock.pack(fill="x")
        steps = [
            {"name": "start", "status": "ok", "duration_ms": 10},
            {"name": "finish", "status": "ok", "duration_ms": 20},
        ]
        index = dock.render(steps, scrub_labels=["chat.started", "chat.complete"], scrub_index=1)
        root.update_idletasks()
        assert index == 1
        dock.scrubber._step_prev()
        root.update_idletasks()
        assert scrubbed[-1] == 0
    finally:
        root.destroy()
