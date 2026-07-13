"""Automation workspace view smoke tests."""

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

from ai_command_center.core.projectors.automation_workspace_projector import (
    AutomationWorkspaceProjector,
)
from ai_command_center.ui.views.automation_workspace_view import AutomationWorkspaceView


def test_automation_workspace_view_smoke() -> None:
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:
        pytest.skip(f"tkinter display unavailable: {exc}")
    try:
        view = AutomationWorkspaceView(root)
        view.pack(fill="both", expand=True)
        view.apply_state(AutomationWorkspaceProjector.project_state(()))
        root.update_idletasks()
    finally:
        root.destroy()
