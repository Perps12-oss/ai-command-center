"""Note inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class NoteInspector(PayloadInspector):
    """Renders a note inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Note", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("title", "content", "text", "path", "summary")

    def preview_label(self) -> str:
        return "Note"


__all__ = ["NoteInspector"]
