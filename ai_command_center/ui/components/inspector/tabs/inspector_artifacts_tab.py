"""InspectorArtifactsTab — artifact list for the inspector panel.

Architecture contract: pure display widget, data supplied via update().
Actions publish via on_artifact_action callback (UI → UIController → bus).
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.core.state.execution_state import ArtifactItem
from ai_command_center.ui.design_system import theme_v2 as T

_KIND_ICONS: dict[str, str] = {
    "text":     "📄",
    "code":     "⌥",
    "image":    "🖼",
    "pdf":      "📕",
    "email":    "✉",
    "calendar": "📅",
    "data":     "📊",
}


class _ArtifactRow(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        artifact_id: str,
        kind: str,
        label: str,
        size_bytes: int,
        on_action: Callable[[str, str], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            height=36,
        )
        self.pack_propagate(False)
        icon = _KIND_ICONS.get(kind, "📄")

        ctk.CTkLabel(
            self,
            text=icon,
            font=(T.FONT_FAMILY, 13),
            width=24,
        ).pack(side="left", padx=(8, 4), pady=6)

        ctk.CTkLabel(
            self,
            text=label or artifact_id[:24],
            font=(T.FONT_FAMILY, 11),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        if size_bytes:
            size_str = (
                f"{size_bytes / 1024:.1f} KB"
                if size_bytes >= 1024
                else f"{size_bytes} B"
            )
            ctk.CTkLabel(
                self,
                text=size_str,
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
            ).pack(side="right", padx=4)

        ctk.CTkButton(
            self,
            text="⤢",
            width=22, height=22,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=lambda: on_action(artifact_id, "preview"),
        ).pack(side="right", padx=4)


class InspectorArtifactsTab(ctk.CTkFrame):
    """Lists artifacts produced by the current execution."""

    def __init__(
        self,
        master: Any,
        on_artifact_action: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_artifact_action = on_artifact_action or (lambda a, k: None)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)

    def update(self, artifacts: Sequence[ArtifactItem]) -> None:
        """Refresh the artifact list from typed :class:`ArtifactItem` projections."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not artifacts:
            ctk.CTkLabel(
                self._scroll,
                text="No artifacts",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=20)
            return

        for art in artifacts:
            _ArtifactRow(
                self._scroll,
                artifact_id=art.artifact_id,
                kind=art.kind or "text",
                label=art.label,
                size_bytes=int(art.size_bytes),
                on_action=self._on_artifact_action,
            ).pack(fill="x", padx=4, pady=2)
