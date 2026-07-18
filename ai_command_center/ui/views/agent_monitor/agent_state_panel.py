"""Agent State — operational diagnosis from projected run fields."""

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


class AgentStatePanel(ctk.CTkFrame):
    """State / error / transition / metadata for the selected or active run."""

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
            text="Agent State",
            font=T.FONT_HEADER,
            text_color=T.AGENT_PURPLE,
            anchor="w",
        ).pack(side="left")
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._empty()

    def apply_snapshot(
        self,
        pipeline: AgentPipelineSnapshot,
        *,
        selected_agent_id: str = "",
    ) -> None:
        run = self._resolve_run(pipeline, selected_agent_id)
        clear_children(self._body)
        if run is None:
            self._empty()
            return
        fg = status_color(run.state)
        self._row("State", run.state or "—", color=fg)
        error = run.error.strip() if run.error else ""
        if error or str(run.state).lower() in {"failed", "error"}:
            self._row("Error", error or "failed (no summary)", color=T.STATUS_ERROR)
        else:
            self._row("Error", "none", color=T.TEXT_MUTED)
        # Last transition is projected as current state + step count (no timestamps).
        self._row("Last Transition", f"{run.state or '—'} · step {run.steps}")
        self._row("Runtime Metadata", self._metadata(run), color=T.TEXT_SECONDARY)

    @staticmethod
    def _resolve_run(
        pipeline: AgentPipelineSnapshot, selected_agent_id: str
    ) -> AgentRunSnapshot | None:
        if selected_agent_id:
            found = pipeline.run_by_id(selected_agent_id)
            if found is not None:
                return found
        if pipeline.active_run is not None:
            return pipeline.active_run
        if pipeline.runs:
            return pipeline.runs[-1]
        return None

    @staticmethod
    def _metadata(run: AgentRunSnapshot) -> str:
        parts = [
            f"id={run.agent_id or '—'}",
            f"role={run.spawn_role or '—'}",
            f"ws={run.workspace_id or '—'}",
            f"entity={run.workspace_entity_id or '—'}",
            f"steps={run.steps}",
        ]
        return " · ".join(parts)

    def _empty(self) -> None:
        clear_children(self._body)
        ctk.CTkLabel(
            self._body,
            text="Select an agent run to inspect operational state.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=4, pady=12)

    def _row(self, label: str, value: str, *, color: str = T.TEXT_PRIMARY) -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(
            frame,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=120,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            frame,
            text=value,
            font=T.FONT_SMALL,
            text_color=color,
            anchor="w",
            wraplength=280,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
