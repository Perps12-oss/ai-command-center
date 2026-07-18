"""Execution History — all projected agent runs (no repository queries)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.agent_pipeline_snapshot import (
    AgentPipelineSnapshot,
    AgentRunSnapshot,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color
from ai_command_center.ui.widget_utils import clear_children


def _duration_label(run: AgentRunSnapshot) -> str:
    """Duration is not projected; surface steps as the available work unit."""
    return f"{run.steps} steps"


class ExecutionHistoryPanel(ctk.CTkFrame):
    """Operational history from agent_pipeline.runs only (N runs → N rows)."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.AGENT_PURPLE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Execution History",
            font=T.FONT_HEADER,
            text_color=T.AGENT_PURPLE,
            anchor="w",
        ).pack(side="left")
        self._count = ctk.CTkLabel(
            header,
            text="0",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._count.pack(side="right")

        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(self, pipeline: AgentPipelineSnapshot) -> None:
        runs = list(pipeline.runs)
        self._count.configure(text=str(len(runs)))
        clear_children(self._body)
        if not runs:
            ctk.CTkLabel(
                self._body,
                text=(
                    "No agent runs projected yet.\n"
                    "History appears after agent pipelines produce run snapshots.\n"
                    "Next: start an agent pipeline from Chat or Goals."
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=12)
            return

        # Newest-last projection order reversed for recent-first display.
        for run in reversed(runs):
            self._add_row(run)

    def _add_row(self, run: AgentRunSnapshot) -> None:
        failed = str(run.state).lower() in {"failed", "error"} or bool(
            str(run.error or "").strip()
        )
        row = ctk.CTkFrame(
            self._body,
            fg_color=T.STATUS_ERROR_BG if failed else "transparent",
            border_color=T.STATUS_ERROR if failed else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        row.pack(fill="x", pady=2)
        fg = status_color(run.state)
        summary = (run.error or "").strip() if failed else (run.task or "—")
        if failed and not summary:
            summary = "failed"
        ctk.CTkLabel(
            row,
            text=f"{run.agent_id} · {run.state} · {_duration_label(run)}",
            font=T.FONT_SMALL,
            text_color=fg,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(4, 0))
        ctk.CTkLabel(
            row,
            text=f"Error summary: {summary[:80]}" if failed else f"Task: {summary[:80]}",
            font=T.FONT_SMALL,
            text_color=T.STATUS_ERROR if failed else T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(0, 4))
