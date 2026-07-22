"""Execution event inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class ExecutionEventInspector(PayloadInspector):
    """Renders an execution event inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Execution Event", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("event_type", "status", "detail", "description", "summary")

    def preview_label(self) -> str:
        return "Event"


__all__ = ["ExecutionEventInspector"]
