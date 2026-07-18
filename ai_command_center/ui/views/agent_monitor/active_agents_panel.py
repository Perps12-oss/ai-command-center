"""Active Agents — projected agent_pipeline.runs with operator sort."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.agent_pipeline_snapshot import (
    AgentPipelineSnapshot,
    AgentRunSnapshot,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color
from ai_command_center.ui.widget_utils import clear_children

# Running → Waiting → Failed → Completed (failures first among inactive).
_STATE_RANK = {
    "running": 0,
    "spawning": 0,
    "waiting": 1,
    "failed": 2,
    "error": 2,
    "terminated": 3,
    "completed": 3,
    "complete": 3,
}


def sort_agent_runs(runs: list[AgentRunSnapshot]) -> list[AgentRunSnapshot]:
    """Operator sort: Running → Waiting → Failed → Completed."""
    return sorted(
        runs,
        key=lambda r: (_STATE_RANK.get(str(r.state).lower(), 5), r.agent_id),
    )


class ActiveAgentsPanel(ctk.CTkFrame):
    """Lists projected agent runs for selection (supporting detail)."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.AGENT_PURPLE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        self._on_select = on_select
        self._selected_id = ""

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Active Agents",
            font=T.FONT_HEADER,
            text_color=T.AGENT_PURPLE,
            anchor="w",
        ).pack(side="left")
        self._count = ctk.CTkLabel(
            header,
            text="0 runs",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._count.pack(side="right")

        self._list = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(
        self,
        pipeline: AgentPipelineSnapshot,
        *,
        selected_agent_id: str = "",
    ) -> None:
        self._selected_id = selected_agent_id
        runs = sort_agent_runs(list(pipeline.runs))
        self._count.configure(text=f"{len(runs)} runs")
        clear_children(self._list)
        if not runs:
            ctk.CTkLabel(
                self._list,
                text="No agent runs in the current projection.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=4, pady=12)
            return
        for run in runs:
            self._add_row(run)

    def _add_row(self, run: AgentRunSnapshot) -> None:
        selected = run.agent_id == self._selected_id
        row = ctk.CTkFrame(
            self._list,
            fg_color=T.BG_GLASS if selected else "transparent",
            border_color=T.AGENT_PURPLE if selected else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        row.pack(fill="x", pady=2)
        fg = status_color(run.state)
        role = run.spawn_role or "—"
        task = (run.task or "—")[:40]
        text = f"{run.agent_id} · {role} · {run.state} · {task}"
        lbl = ctk.CTkLabel(
            row,
            text=text,
            font=T.FONT_SMALL,
            text_color=fg,
            anchor="w",
            justify="left",
        )
        lbl.pack(fill="x", padx=8, pady=4)
        meta = ctk.CTkLabel(
            row,
            text=f"workspace: {run.workspace_id or '—'}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        meta.pack(fill="x", padx=8, pady=(0, 4))

        agent_id = run.agent_id

        def _select(_event: Any = None, _aid: str = agent_id) -> None:
            if self._on_select:
                self._on_select(_aid)

        row.bind("<Button-1>", _select)
        lbl.bind("<Button-1>", _select)
        meta.bind("<Button-1>", _select)
