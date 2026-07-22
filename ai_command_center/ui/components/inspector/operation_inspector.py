"""Operation inspector widget for Mission Control."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class OperationInspector(PayloadInspector):
    """Renders an operation inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Operation", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("name", "correlation_id", "status", "goal_title")

    def preview_label(self) -> str:
        return "Operation"


__all__ = ["OperationInspector"]
