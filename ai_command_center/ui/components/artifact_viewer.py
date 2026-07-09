"""ArtifactViewer — preview stub for artifact types.

Supported preview types: markdown, code, image, pdf (stub), email, calendar.

Architecture contract: pure display widget, no bus/service imports.
Actions publish via on_action callback (→ UIController → bus ui.artifact.action).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.renderers.artifact_renderer_factory import ArtifactRendererFactory


class ArtifactViewer(ctk.CTkFrame):
    """Preview panel for a single artifact.

    Dispatches to the appropriate sub-renderer based on ``kind``.
    Falls back to a plain text view for unknown kinds.
    """

    def __init__(
        self,
        master: Any,
        *,
        on_action: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_DEEP,
            corner_radius=T.CORNER_RADIUS,
            **kwargs,
        )
        self._on_action = on_action or (lambda a, k: None)
        self._artifact_id = ""

        self._header = ctk.CTkFrame(
            self,
            fg_color=T.BG_PANEL,
            corner_radius=0,
            height=36,
        )
        self._header.pack(fill="x")
        self._header.pack_propagate(False)

        self._title_lbl = ctk.CTkLabel(
            self._header,
            text="Artifact Viewer",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._title_lbl.pack(side="left", padx=10, pady=8)

        ctk.CTkButton(
            self._header,
            text="✕",
            width=24, height=24,
            font=(T.FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=T.BG_GLASS,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=lambda: self._on_action(self._artifact_id, "close"),
        ).pack(side="right", padx=8, pady=6)

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=12, pady=10)

    def show(
        self,
        artifact_id: str,
        kind: str,
        label: str,
        content: str = "",
    ) -> None:
        """Display an artifact in the viewer."""
        self._artifact_id = artifact_id
        self._title_lbl.configure(text=label or artifact_id[:32])

        for child in self._content.winfo_children():
            child.destroy()

        normalized = ArtifactRendererFactory.normalize_kind(kind)
        if ArtifactRendererFactory.is_stub_kind(normalized):
            self._show_stub(normalized)
        elif ArtifactRendererFactory.uses_text_preview(normalized):
            preview = ArtifactRendererFactory.preview_content(
                kind=normalized,
                content=content,
                label=label,
            )
            self._show_text(
                preview,
                monospace=ArtifactRendererFactory.uses_monospace(normalized),
            )
        else:
            preview = ArtifactRendererFactory.preview_content(
                kind=normalized,
                content=content,
                label=label,
            )
            self._show_text(preview, monospace=False)

    def _show_text(self, content: str, *, monospace: bool) -> None:
        font = ("Consolas", 11) if monospace else T.FONT_BODY
        tb = ctk.CTkTextbox(
            self._content,
            wrap="word",
            font=font,
            fg_color=T.BG_INPUT,
            text_color=T.TEXT_PRIMARY,
            border_width=0,
        )
        tb.pack(fill="both", expand=True)
        tb.insert("end", content or "(empty)")
        tb.configure(state="disabled")

    def _show_stub(self, kind: str) -> None:
        msg = ArtifactRendererFactory.stub_message(kind)
        ctk.CTkLabel(
            self._content,
            text=msg,
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
            wraplength=300,
        ).pack(pady=40)
