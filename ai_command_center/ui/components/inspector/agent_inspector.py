"""Agent inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class AgentInspector(PayloadInspector):
    """Renders an agent inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Agent", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("name", "agent_id", "role", "status", "task")

    def preview_label(self) -> str:
        return "Agent"


__all__ = ["AgentInspector"]
