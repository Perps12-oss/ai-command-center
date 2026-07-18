"""Execution Center workspace — Article 13 operational surface (Phase 11C).

Architecture contract:
- Pure renderer. Reads AppState via apply_state(snapshot) only.
- No repositories, services, or direct execution subscriptions.
- Receipt/Truth panels visualize orchestration_run only.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.execution_center import (
    ExecutionDetailPanel,
    ExecutionListPanel,
    ExecutionTimelinePanel,
    ReceiptViewerPanel,
    TruthValidationPanel,
)
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    domain_error_from_snap,
    set_surface_state,
)


class ExecutionsView(ctk.CTkFrame):
    """Execution Center orchestration shell (Hero + five Article 13 panels)."""

    def __init__(
        self,
        master: Any,
        on_select: Callable[[str], None] | None = None,
        on_scrub: Callable[[str, int], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_select = on_select or (lambda _rid: None)
        self._on_scrub = on_scrub or (lambda _rid, _i: None)
        self._on_navigate = on_navigate
        self._selected_request_id = ""
        self._last_snap: AppState | None = None
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.EXECUTION_BLUE)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            top,
            text="Execution Center",
            font=T.FONT_TITLE,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(side="left")
        self._metrics = ctk.CTkLabel(
            top,
            text="0 active · 0 total · 0 failed · —% success",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._metrics.pack(side="right")

        bottom = ctk.CTkFrame(self._hero, fg_color="transparent")
        bottom.pack(fill="x", padx=T.PAD, pady=(8, T.PAD))
        self._hero_hint = ctk.CTkLabel(
            bottom,
            text="No active execution",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._hero_hint.pack(side="left")
        self._hero_action = ctk.CTkButton(
            bottom,
            text="No Executions",
            font=T.FONT_BODY,
            fg_color=T.EXECUTION_BLUE,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            height=28,
            width=180,
            state="disabled",
            command=self._on_hero_action,
        )
        self._hero_action.pack(side="right")
        self._hero_target_id = ""

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
        body.grid_rowconfigure(0, weight=2)
        body.grid_rowconfigure(1, weight=2)
        body.grid_rowconfigure(2, weight=1)

        self._list = ExecutionListPanel(body, on_select=self._select)
        self._list.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        self._timeline = ExecutionTimelinePanel(body, on_scrub=self._scrub)
        self._timeline.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=(0, 8))
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._detail = ExecutionDetailPanel(right)
        self._detail.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        evidence = ctk.CTkFrame(right, fg_color="transparent")
        evidence.grid(row=1, column=0, sticky="nsew")
        evidence.grid_columnconfigure(0, weight=1)
        evidence.grid_columnconfigure(1, weight=1)
        evidence.grid_rowconfigure(0, weight=1)

        self._receipt = ReceiptViewerPanel(evidence)
        self._receipt.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self._truth = TruthValidationPanel(evidence)
        self._truth.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # Keep journal-like bottom strip for timeline overflow / status
        self._status_bar = ctk.CTkLabel(
            body,
            text="Receipt and Truth panels project orchestration_run only.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

    def apply_state(self, snapshot: AppState | list[Any] | None) -> None:
        """Project AppState into all panels. List[Any] legacy path ignored."""
        if snapshot is None:
            set_surface_state(self._surface_state, kind="loading")
            self._hero_target_id = ""
            self._hero_action.configure(text="No Executions", state="disabled")
            return
        if not isinstance(snapshot, AppState):
            return
        self._last_snap = snapshot
        lib = snapshot.execution_library
        history = list(lib.run_history)
        total = lib.total_runs or len(history) or len(snapshot.execution_runs)
        failed = sum(1 for r in history if str(r.status).lower() in {"failed", "error"})
        active = 1 if lib.active_plan.is_active else 0
        complete = sum(
            1 for r in history if str(r.status).lower() in {"complete", "completed", "success"}
        )
        success_rate = f"{int((complete / total) * 100)}%" if total else "—"
        self._metrics.configure(
            text=f"{active} active · {total} total · {failed} failed · {success_rate} success"
        )

        plan_error = str(getattr(lib.active_plan, "error", "") or "").strip()
        err = plan_error or domain_error_from_snap(
            snapshot,
            topic_prefixes=("execution.", "orchestration.", "tool."),
        )
        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif total == 0 and not lib.active_plan.is_active:
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="No execution runs are projected yet.",
                    creates="Runs appear when Chat, Goals, or Agents start an orchestration.",
                    next_action="Open Chat or Goals and start a task that executes.",
                ),
            )
        else:
            set_surface_state(self._surface_state, kind="data")

        if lib.active_plan.is_active:
            target = lib.active_plan.request_id or lib.active_plan.run_id
            self._hero_target_id = target
            step = lib.active_plan.current_step
            step_name = (step.capability or step.step_id) if step else "—"
            self._hero_hint.configure(
                text=f"Active: {target[:24] or 'run'} · step {step_name}"
            )
            self._hero_action.configure(text="View Active Execution", state="normal")
        else:
            latest = lib.last_run
            if latest is None and snapshot.execution_runs:
                run = snapshot.execution_runs[-1]
                self._hero_target_id = run.request_id or run.run_id
            elif latest is not None:
                self._hero_target_id = latest.request_id or latest.run_id
            else:
                self._hero_target_id = ""
            self._hero_hint.configure(
                text="No active execution"
                if not self._hero_target_id
                else f"Latest: {self._hero_target_id[:24]}"
            )
            if self._hero_target_id:
                self._hero_action.configure(text="Open Latest Execution", state="normal")
            else:
                self._hero_action.configure(text="No Executions", state="disabled")

        selected = self._selected_request_id
        self._list.apply_snapshot(snapshot, selected_request_id=selected)
        self._timeline.apply_snapshot(snapshot, selected_request_id=selected)
        self._detail.apply_snapshot(snapshot, selected_request_id=selected)
        self._receipt.apply_snapshot(snapshot, selected_request_id=selected)
        self._truth.apply_snapshot(snapshot, selected_request_id=selected)

    def apply_timeline(
        self,
        *,
        request_id: str,
        timeline_steps: Sequence[dict[str, Any]],
        scrub_labels: Sequence[str],
        scrub_index: int,
        timeline_source: str,
        spans: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        """Scrubber projection compatibility for StateApplier."""
        del spans
        if request_id and request_id != self._selected_request_id:
            return
        self._timeline.apply_timeline(
            request_id=request_id,
            timeline_steps=timeline_steps,
            scrub_labels=scrub_labels,
            scrub_index=scrub_index,
            timeline_source=timeline_source,
        )

    def open_request(self, request_id: str) -> None:
        self._select(request_id)

    def _select(self, request_id: str) -> None:
        self._selected_request_id = request_id
        self._on_select(request_id)
        if self._last_snap is not None:
            self.apply_state(self._last_snap)

    def _scrub(self, index: int) -> None:
        if self._selected_request_id:
            self._on_scrub(self._selected_request_id, index)

    def _on_hero_action(self) -> None:
        # Guard: never silently no-op while the control looks enabled.
        if str(self._hero_action.cget("state")) == "disabled" or not self._hero_target_id:
            return
        self._select(self._hero_target_id)
