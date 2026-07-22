"""Memory inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class MemoryInspector(PayloadInspector):
    """Renders a memory inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Memory", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("label", "content", "text", "summary", "description")

    def preview_label(self) -> str:
        return "Memory"


__all__ = ["MemoryInspector"]
