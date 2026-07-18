"""Agent dashboard — real AppState projection, no placeholder."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color


class AgentsView(ctk.CTkFrame):
    """Displays active agents, pipeline stage, and planned tools."""

    def __init__(
        self,
        master,
        on_command: Callable[[str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_command = on_command
        self._on_navigate = on_navigate
        self._build()

    def _build(self) -> None:
        pipeline_card = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        pipeline_card.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        ctk.CTkLabel(
            pipeline_card,
            text="Agent Pipeline",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._stage_label = ctk.CTkLabel(
            pipeline_card,
            text="No active pipeline",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._stage_label.pack(fill="x", padx=T.PAD, pady=(0, 4))

        self._tools_label = ctk.CTkLabel(
            pipeline_card,
            text="Planned tools: —",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._tools_label.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        runs_card = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        runs_card.pack(fill="both", expand=True, padx=T.PAD, pady=(8, T.PAD))

        ctk.CTkLabel(
            runs_card,
            text="Active Agent Runs",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._runs_list = ctk.CTkFrame(runs_card, fg_color="transparent")
        self._runs_list.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        self._run_rows: list[ctk.CTkLabel] = []
        for _ in range(10):
            lbl = ctk.CTkLabel(
                self._runs_list,
                text="",
                font=T.FONT_BODY,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                justify="left",
            )
            lbl.pack(fill="x", pady=(0, 2))
            self._run_rows.append(lbl)

    def apply_state(self, snap: Any) -> None:
        """Project agent pipeline and active runs into the view."""
        agent_pipeline = getattr(snap, "agent_pipeline", None)

        pipeline_id = getattr(agent_pipeline, "pipeline_id", "") if agent_pipeline else ""
        stage = getattr(agent_pipeline, "pipeline_stage", "") if agent_pipeline else ""
        planned = getattr(agent_pipeline, "planned_tools", ()) if agent_pipeline else ()

        if pipeline_id:
            self._stage_label.configure(
                text=f"Pipeline {pipeline_id}: {stage}",
                text_color=T.TEXT_PRIMARY,
            )
        else:
            self._stage_label.configure(text="No active pipeline", text_color=T.TEXT_SECONDARY)

        tools = ", ".join(planned) if planned else "—"
        self._tools_label.configure(text=f"Planned tools: {tools}")

        runs = list(getattr(agent_pipeline, "runs", ()) if agent_pipeline else ())
        active = [r for r in runs if getattr(r, "is_active", False)]

        for i, lbl in enumerate(self._run_rows):
            if i < len(active):
                run = active[i]
                state = getattr(run, "state", "")
                agent_id = getattr(run, "agent_id", "")
                task = getattr(run, "task", "")
                steps = getattr(run, "steps", 0)
                fg = status_color(state)
                text = f"{agent_id}: {state} ({steps} steps) {task}".strip()
                lbl.configure(text=text, text_color=fg)
            else:
                lbl.configure(text="", text_color=T.TEXT_SECONDARY)
