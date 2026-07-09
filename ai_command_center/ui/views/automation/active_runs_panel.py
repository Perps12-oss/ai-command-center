"""Active workflow runs panel."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.automation_workspace import AutomationRunItem
from ai_command_center.ui.design_system import theme_v2 as T


class ActiveRunsPanel(ctk.CTkFrame):
    """Trigger.dev-style live run progress list."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, corner_radius=0, **kwargs)
        ctk.CTkLabel(
            self,
            text="ACTIVE RUNS",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def update(self, runs: Sequence[AutomationRunItem]) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        if not runs:
            ctk.CTkLabel(
                self._scroll,
                text="No active runs",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(anchor="w", pady=8)
            return
        for run in runs:
            row = ctk.CTkFrame(self._scroll, fg_color=T.BG_GLASS, corner_radius=T.SMALL_RADIUS)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(
                row,
                text=run.title,
                font=(T.FONT_FAMILY, 11),
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 2))
            bar = ctk.CTkProgressBar(
                row,
                height=6,
                progress_color=T.STATUS_BUSY,
                fg_color=T.BG_GLASS_BORDER,
            )
            bar.set(max(0.0, min(1.0, run.progress)))
            bar.pack(fill="x", padx=10, pady=(0, 4))
            step_text = (
                f"Step {run.current_step_index + 1}/{max(run.total_steps, 1)}"
                if run.total_steps
                else run.state
            )
            ctk.CTkLabel(
                row,
                text=step_text,
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 8))


__all__ = ["ActiveRunsPanel"]
