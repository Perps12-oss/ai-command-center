"""Static workflow node library palette (Slice 1)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

NODE_LIBRARY_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Planning", ("Plan", "Route", "Summarize")),
    ("Providers", ("Ollama", "OpenAI", "QwenPaw")),
    ("Tools", ("Shell", "Search", "Write File")),
    ("Artifacts", ("Artifact", "Decision", "Report")),
    ("Inspectors", ("Trace", "Provider", "Timeline")),
    ("Automation", ("Trigger", "Schedule", "Webhook")),
    ("Memory", ("Remember", "Recall", "Forget")),
    ("External", ("HTTP", "Webhook", "MCP")),
)


class WorkflowNodeLibrary(ctk.CTkFrame):
    """Left-rail palette of static node categories."""

    def __init__(
        self,
        master: Any,
        *,
        on_preview: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._on_preview = on_preview or (lambda _category, _label: None)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self,
            text="NODE LIBRARY",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=4, pady=(0, T.PAD))

        for category, labels in NODE_LIBRARY_CATEGORIES:
            section = ctk.CTkFrame(scroll, fg_color=T.BG_GLASS, corner_radius=T.SMALL_RADIUS)
            section.pack(fill="x", padx=4, pady=4)
            ctk.CTkLabel(
                section,
                text=category,
                font=(T.FONT_FAMILY, 10, "bold"),
                text_color=T.TEXT_SECONDARY,
                anchor="w",
            ).pack(fill="x", padx=8, pady=(6, 2))
            for label in labels:
                ctk.CTkButton(
                    section,
                    text=label,
                    height=24,
                    font=(T.FONT_FAMILY, 10),
                    fg_color="transparent",
                    hover_color=T.BG_GLASS_BORDER,
                    text_color=T.TEXT_MUTED,
                    anchor="w",
                    command=lambda c=category, lbl=label: self._on_preview(c, lbl),
                ).pack(fill="x", padx=6, pady=1)


__all__ = ["NODE_LIBRARY_CATEGORIES", "WorkflowNodeLibrary"]
