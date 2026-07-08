"""Message inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class MessageInspector(PayloadInspector):
    """Renders a message inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Message", **kwargs)


__all__ = ["MessageInspector"]
