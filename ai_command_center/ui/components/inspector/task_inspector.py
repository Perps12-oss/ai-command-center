"""Task inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class TaskInspector(PayloadInspector):
    """Renders a task inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Task", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("title", "task", "description", "summary", "status")

    def preview_label(self) -> str:
        return "Task"


__all__ = ["TaskInspector"]
