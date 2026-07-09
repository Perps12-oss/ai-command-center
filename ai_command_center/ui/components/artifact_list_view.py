"""ArtifactListView — vertical list of artifact cards for chat and inspector.

Architecture contract: pure display widget, no bus/service imports.
Data supplied via set_artifacts() from AppState projections.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.core.state.artifact_state import ArtifactCatalogItem
from ai_command_center.ui.views.chat.artifact_card import ArtifactCard
from ai_command_center.ui.widget_utils import clear_children


def _preview_snippet(content: str, *, max_len: int = 72) -> str:
    line = content.strip().splitlines()[0] if content.strip() else ""
    if len(line) <= max_len:
        return line
    return line[: max_len - 1] + "…"


class ArtifactListView(ctk.CTkFrame):
    """Renders ArtifactCard rows for a scoped artifact catalog slice."""

    def __init__(
        self,
        master: Any,
        *,
        on_action: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_action = on_action or (lambda _aid, _act: None)
        self._artifacts: tuple[ArtifactCatalogItem, ...] = ()

    def set_artifacts(self, artifacts: Sequence[ArtifactCatalogItem]) -> None:
        """Rebuild cards when the artifact catalog slice changes."""
        catalog = tuple(artifacts)
        if catalog == self._artifacts:
            return
        self._artifacts = catalog
        clear_children(self)
        if not catalog:
            return
        for art in catalog:
            ArtifactCard(
                self,
                artifact_id=art.artifact_id,
                kind=art.kind,
                label=art.label,
                size_bytes=art.size_bytes,
                preview_snippet=_preview_snippet(art.content),
                on_action=self._on_action,
            ).pack(fill="x", pady=(0, 4))

    def artifact_count(self) -> int:
        return len(self._artifacts)


__all__ = ["ArtifactListView", "_preview_snippet"]
