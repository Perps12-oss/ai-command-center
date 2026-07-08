"""Provider inspector widget."""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.components.inspector.payload_inspector import PayloadInspector


class ProviderInspector(PayloadInspector):
    """Renders a single provider inspection payload."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fallback_title="Provider", **kwargs)


__all__ = ["ProviderInspector"]
