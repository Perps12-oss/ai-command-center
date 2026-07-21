"""World node inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class WorldNodeInspector(PayloadInspector):
    """Renders a world-model node inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="World Node", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("name", "title", "type", "label", "summary")

    def preview_label(self) -> str:
        return "Node"


__all__ = ["WorldNodeInspector"]
