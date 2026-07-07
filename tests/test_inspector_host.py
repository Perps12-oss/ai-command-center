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
from ai_command_center.ui.components.inspector import InspectorHost, MessageInspector


def test_inspector_host_smoke() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        host = InspectorHost(root)
        host.pack(fill="both", expand=True)
        host.register("message", MessageInspector(host))

        ref = InspectableRef.from_payload(
            {
                "kind": "message",
                "ref_id": "msg-1",
                "label": "Hello world",
                "payload": {
                    "role": "user",
                    "content": "Hello there",
                    "request_id": "r1",
                },
            }
        )
        host.show(ref)
        root.update_idletasks()

        assert host._title.cget("text") == "Hello world"

        host.clear()
        root.update_idletasks()
    finally:
        root.destroy()
