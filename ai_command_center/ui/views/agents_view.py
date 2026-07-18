"""Agent Monitor workspace — Article 14 operational surface (Phase 11D).

Architecture contract:
- Pure renderer. Reads AppState via apply_state(snapshot) only.
- Uses AppState.agent_pipeline / AgentPipelineSnapshot exclusively.
- Cancel publishes AGENT_CANCEL_REQUEST through callback (never direct runtime).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.agent_pipeline_snapshot import AgentPipelineSnapshot
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.agent_monitor import (
    ActiveAgentsPanel,
    AgentStatePanel,
    ExecutionHistoryPanel,
    PipelineProgressPanel,
    TaskAssignmentPanel,
)
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    domain_error_from_snap,
    set_surface_state,
)


class AgentsView(ctk.CTkFrame):
    """Agent Monitor orchestration shell (Hero + five Article 14 panels)."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
        on_cancel: Callable[[str, str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        on_command: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_select = on_select or (lambda _aid: None)
        self._on_cancel = on_cancel or (lambda _aid, _reason: None)
        self._on_navigate = on_navigate
        self._on_command = on_command
        self._selected_agent_id = ""
        self._cancel_agent_id = ""
        self._cancel_context = ""
        self._last_pipeline: AgentPipelineSnapshot | None = None
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.AGENT_PURPLE)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            top,
            text="Agent Monitor",
            font=T.FONT_TITLE,
            text_color=T.AGENT_PURPLE,
            anchor="w",
        ).pack(side="left")
        self._metrics = ctk.CTkLabel(
            top,
            text="0 active · stage — · 0 tools · 0 running · 0 failed",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._metrics.pack(side="right")

        bottom = ctk.CTkFrame(self._hero, fg_color="transparent")
        bottom.pack(fill="x", padx=T.PAD, pady=(8, T.PAD))
        self._hero_hint = ctk.CTkLabel(
            bottom,
            text="No active pipeline or agent run",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._hero_hint.pack(side="left")
        self._hero_action = ctk.CTkButton(
            bottom,
            text="Cancel Active Pipeline",
            font=T.FONT_BODY,
            fg_color=T.AGENT_PURPLE,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            height=28,
            width=200,
            state="disabled",
            command=self._on_hero_cancel,
        )
        self._hero_action.pack(side="right")

        self._surface_state = ctk.CTkLabel(
            self._hero,
            text="Loading…",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self._surface_state.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        # Pipeline Progress dominates (row 0 weight highest).
        body.grid_rowconfigure(0, weight=3)
        body.grid_rowconfigure(1, weight=2)
        body.grid_rowconfigure(2, weight=2)

        self._pipeline = PipelineProgressPanel(body)
        self._pipeline.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 8))

        self._agents = ActiveAgentsPanel(body, on_select=self._select)
        self._agents.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        self._state = AgentStatePanel(body)
        self._state.grid(row=1, column=1, sticky="nsew", pady=(0, 8))

        self._tasks = TaskAssignmentPanel(body)
        self._tasks.grid(row=2, column=0, sticky="nsew", padx=(0, 8))

        self._history = ExecutionHistoryPanel(body)
        self._history.grid(row=2, column=1, sticky="nsew")

    def apply_state(self, snapshot: AppState | Any | None) -> None:
        """Project AppState.agent_pipeline into Hero + all panels."""
        if snapshot is None:
            set_surface_state(
                self._surface_state,
                kind="loading",
                message=article18_loading(
                    status="Status: loading Agent Monitor",
                    what="agent_pipeline runs and pipeline stage",
                    next_action="Wait for AppState refresh; then cancel or inspect a run.",
                ),
            )
            return
        if isinstance(snapshot, AppState):
            pipeline = snapshot.agent_pipeline
            err = domain_error_from_snap(
                snapshot,
                topic_prefixes=("agent.", "pipeline."),
            )
        else:
            pipeline = getattr(snapshot, "agent_pipeline", None)
            if pipeline is None:
                return
            err = ""
        self._last_pipeline = pipeline

        active = list(pipeline.active_runs)
        failed = [
            r
            for r in pipeline.runs
            if str(r.state).lower() in {"failed", "error"}
            or bool(str(r.error or "").strip())
        ]
        running = [
            r for r in active if str(r.state).lower() in {"running", "spawning"}
        ]
        stage = pipeline.pipeline_stage or "—"
        planned_n = len(pipeline.planned_tools)
        self._metrics.configure(
            text=(
                f"{len(active)} active · stage {stage} · {planned_n} tools · "
                f"{len(running)} running · {len(failed)} failed"
            )
        )
        if failed:
            self._metrics.configure(text_color=T.STATUS_ERROR)
        else:
            self._metrics.configure(text_color=T.TEXT_SECONDARY)

        fail_msg = ""
        if failed:
            first = failed[0]
            fail_msg = str(getattr(first, "error", "") or "").strip() or (
                f"Agent run {first.agent_id} is in state {first.state}."
            )
        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif fail_msg:
            set_surface_state(self._surface_state, kind="error", message=fail_msg)
        elif not pipeline.runs and not pipeline.pipeline_active:
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="No agent pipeline or agent runs are projected yet.",
                    creates="Agent runs appear when a multi-agent pipeline or "
                    "supervised agent is started.",
                    next_action="Start an agent pipeline from Chat or Goals.",
                ),
            )
        else:
            set_surface_state(self._surface_state, kind="data")

        self._update_cancel_context(pipeline)
        selected = self._selected_agent_id or pipeline.active_run_id

        self._pipeline.apply_snapshot(pipeline)
        self._agents.apply_snapshot(pipeline, selected_agent_id=selected)
        self._state.apply_snapshot(pipeline, selected_agent_id=selected)
        self._tasks.apply_snapshot(pipeline, selected_agent_id=selected)
        self._history.apply_snapshot(pipeline)

    def _update_cancel_context(self, pipeline: AgentPipelineSnapshot) -> None:
        """Contextual cancel: Active Pipeline or Selected Agent Run only."""
        selected = self._selected_agent_id
        selected_run = pipeline.run_by_id(selected) if selected else None
        selected_active = bool(selected_run and selected_run.is_active)

        if pipeline.pipeline_active and pipeline.active_run_id:
            self._cancel_agent_id = pipeline.active_run_id
            self._cancel_context = "pipeline"
            label = f"Cancel Active Pipeline ({pipeline.pipeline_id[:16]})"
            hint = f"Active Pipeline: {pipeline.pipeline_id} · stage {pipeline.pipeline_stage}"
            enabled = True
        elif selected_active and selected_run is not None:
            self._cancel_agent_id = selected_run.agent_id
            self._cancel_context = "selected"
            label = f"Cancel Selected Agent Run ({selected_run.agent_id[:16]})"
            hint = f"Selected Agent Run: {selected_run.agent_id} · {selected_run.state}"
            enabled = True
        elif pipeline.active_run_id:
            self._cancel_agent_id = pipeline.active_run_id
            self._cancel_context = "active"
            label = f"Cancel Selected Agent Run ({pipeline.active_run_id[:16]})"
            hint = f"Active Agent Run: {pipeline.active_run_id}"
            enabled = True
        else:
            self._cancel_agent_id = ""
            self._cancel_context = ""
            label = "Cancel Active Pipeline"
            hint = "No active pipeline or agent run"
            enabled = False

        self._hero_hint.configure(text=hint)
        self._hero_action.configure(
            text=label,
            state="normal" if enabled else "disabled",
        )

    def _select(self, agent_id: str) -> None:
        self._selected_agent_id = str(agent_id)
        self._on_select(self._selected_agent_id)
        if self._last_pipeline is not None:
            self._update_cancel_context(self._last_pipeline)
            self._agents.apply_snapshot(
                self._last_pipeline, selected_agent_id=self._selected_agent_id
            )
            self._state.apply_snapshot(
                self._last_pipeline, selected_agent_id=self._selected_agent_id
            )
            self._tasks.apply_snapshot(
                self._last_pipeline, selected_agent_id=self._selected_agent_id
            )

    def _on_hero_cancel(self) -> None:
        if not self._cancel_agent_id:
            return
        reason = (
            "cancel_active_pipeline"
            if self._cancel_context == "pipeline"
            else "cancel_selected_agent_run"
        )
        self._on_cancel(self._cancel_agent_id, reason)
