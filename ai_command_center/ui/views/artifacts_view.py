"""ArtifactsView — Artifact Center page (Artifact OS).

Lists all artifacts produced across executions, grouped by kind.
Clicking an artifact opens the ArtifactViewer.

Architecture contract: pure display view, no bus/service imports.
Data supplied via apply_state() from the UIQueue.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.core.state.artifact_state import ArtifactCatalogItem

from ai_command_center.ui.components.artifact_viewer import ArtifactViewer
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.artifact_card import ArtifactCard

_KIND_ICONS = {
    "text":     "📄",
    "code":     "⌥",
    "image":    "🖼",
    "pdf":      "📕",
    "email":    "✉",
    "calendar": "📅",
    "data":     "📊",
    "markdown": "✦",
}


class ArtifactsView(ctk.CTkFrame):
    """Artifact Center — full-page artifact library."""

    def __init__(
        self,
        master: Any,
        on_artifact_action: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_artifact_action = on_artifact_action or (lambda a, k: None)
        self._build()

    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Artifacts",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=T.PAD, pady=12)

        # Split: left list + right preview
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True)

        # Left: artifact list
        list_frame = ctk.CTkFrame(split, fg_color=T.BG_PANEL, corner_radius=0, width=320)
        list_frame.pack(side="left", fill="y")
        list_frame.pack_propagate(False)

        ctk.CTkLabel(
            list_frame,
            text="All Artifacts",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        self._scroll = ctk.CTkScrollableFrame(
            list_frame, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True, padx=4)

        # Right: artifact viewer
        right = ctk.CTkFrame(split, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        self._viewer = ArtifactViewer(
            right,
            on_action=self._on_artifact_action,
        )
        self._viewer.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)

        # Default state
        ctk.CTkLabel(
            self._scroll,
            text="No artifacts yet.",
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
        ).pack(pady=40)

    def apply_state(self, artifacts: Sequence[ArtifactCatalogItem]) -> None:
        """Refresh the artifact list from typed AppState projections."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not artifacts:
            ctk.CTkLabel(
                self._scroll,
                text="No artifacts yet.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(pady=40)
            return

        for art in artifacts:
            ArtifactCard(
                self._scroll,
                artifact_id=art.artifact_id,
                kind=art.kind,
                label=art.label,
                size_bytes=art.size_bytes,
                on_action=self._handle_artifact_action,
            ).pack(fill="x", pady=3)

    def _handle_artifact_action(self, artifact_id: str, action: str) -> None:
        selected = next(
            (art for art in getattr(self, "_current_artifacts", ()) if art.artifact_id == artifact_id),
            None,
        )
        if action == "preview":
            if selected is not None:
                self._viewer.show(
                    selected.artifact_id,
                    kind=selected.kind,
                    label=selected.label,
                    content=selected.content,
                )
            else:
                self._viewer.show(artifact_id, kind="text", label=artifact_id)
        self._on_artifact_action(artifact_id, action)

    def set_artifacts(self, artifacts: Sequence[ArtifactCatalogItem]) -> None:
        """Store the latest catalog for preview actions."""
        self._current_artifacts = tuple(artifacts)
        self.apply_state(artifacts)
