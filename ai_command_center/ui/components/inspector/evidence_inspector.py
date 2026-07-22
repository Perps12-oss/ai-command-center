"""Evidence claim inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class EvidenceInspector(PayloadInspector):
    """Renders an evidence/claim inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Evidence", **kwargs)

    def preview_keys(self) -> tuple[str, ...]:
        return ("claim", "truth", "receipt_id", "trace_id", "request_id")

    def preview_label(self) -> str:
        return "Evidence"


__all__ = ["EvidenceInspector"]
