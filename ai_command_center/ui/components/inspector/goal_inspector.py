"""Goal inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class GoalInspector(PayloadInspector):
    """Renders a goal inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Goal", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("title", "goal", "description", "summary", "status")

    def preview_label(self) -> str:
        return "Goal"


__all__ = ["GoalInspector"]
