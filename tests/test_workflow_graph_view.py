"""Workflow graph view smoke tests."""

from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _root = tk.Tk()
    _root.withdraw()
    _root.destroy()
except Exception as exc:  # pragma: no cover
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

from ai_command_center.core.state.workflow_graph_state import WorkflowGraphState
from ai_command_center.ui.views.workflow_graph_view import WorkflowGraphView


def test_workflow_graph_view_smoke() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        view = WorkflowGraphView(root)
        view.pack(fill="both", expand=True)
        state = WorkflowGraphState(
            workflow_id="demo",
            workflow_name="Demo Workflow",
            running=True,
        )
        view.apply_state(state)
        root.update_idletasks()
    finally:
        root.destroy()
