"""Mission Control Operations — live pipeline stages + timeline scrubber (PR-UI-E11).

Architecture contract:
- Pure renderer. Reads AppState via apply_state only.
- Reuses ExecutionTimelineDock (no parallel timeline engine).
- Scrub / select intents via callbacks → UI_OPERATION_* / inspect (shell).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.domain.journal_entry import JournalEntry
from ai_command_center.domain.operation_snapshot import OperationSnapshot
from ai_command_center.ui.components.docks.execution_timeline_dock import (
    ExecutionTimelineDock,
)
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.components.operations import (
    OperationCard,
    PipelineStageStrip,
    resolve_active_stage_index,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    domain_error_from_snap,
    set_surface_state,
)
from ai_command_center.ui.widget_utils import clear_children


def journal_to_timeline_steps(
    journal: tuple[JournalEntry, ...],
) -> list[dict[str, object]]:
    """Project operation journal entries into TimelineRenderer tiles."""
    steps: list[dict[str, object]] = []
    for entry in journal[-40:]:
        kind = entry.kind.value if hasattr(entry.kind, "value") else str(entry.kind)
        steps.append(
            {
                "name": (entry.summary or kind)[:28],
                "status": "completed",
                "duration_ms": 0,
                "entry_id": entry.entry_id,
                "kind": kind,
                "object_id": entry.object_id,
                "correlation_id": entry.correlation_id,
            }
        )
    return steps


def scrubber_events_to_steps(events: tuple[Any, ...]) -> list[dict[str, object]]:
    """Fallback: project execution_scrubber events into timeline tiles."""
    steps: list[dict[str, object]] = []
    for event in events:
        name = str(
            getattr(event, "event_type", "")
            or getattr(event, "summary", "")
            or getattr(event, "name", "")
            or "event"
        )
        status = str(getattr(event, "status", "") or "completed")
        steps.append(
            {
                "name": name[:28],
                "status": status,
                "duration_ms": float(getattr(event, "duration_ms", 0) or 0),
                "event_id": str(getattr(event, "event_id", "") or ""),
                "kind": name,
            }
        )
    return steps


class OperationsView(ctk.CTkFrame):
    """Mission Control: stages, operation roster, scrubbable timeline."""

    def __init__(
        self,
        master: Any,
        *,
        on_select_operation: Callable[[str], None] | None = None,
        on_scrub: Callable[[int, dict[str, object]], None] | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_select_operation = on_select_operation
        self._on_scrub = on_scrub
        self._on_inspect_select = on_inspect_select
        self._on_navigate = on_navigate
        self._selected_correlation_id = ""
        self._scrub_index = 0
        self._timeline_steps: list[dict[str, object]] = []
        self._last_snap: AppState | None = None
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.EXECUTION_BLUE)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            top,
            text="Mission Control Operations",
            font=T.FONT_TITLE,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(side="left")
        self._metrics = ctk.CTkLabel(
            top,
            text="0 operations · 0 journal",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._metrics.pack(side="right")

        self._hint = ctk.CTkLabel(
            self._hero,
            text="Waiting for operation library / pipeline projection…",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._hint.pack(fill="x", padx=T.PAD, pady=(8, 4))

        if self._on_navigate is not None:
            nav = ctk.CTkFrame(self._hero, fg_color="transparent")
            nav.pack(fill="x", padx=T.PAD, pady=(0, 8))
            ctk.CTkButton(
                nav,
                text="Evidence",
                width=100,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.EXECUTION_BLUE,
                command=lambda: self._on_navigate("evidence"),
            ).pack(side="right", padx=(6, 0))
            ctk.CTkButton(
                nav,
                text="Agents",
                width=90,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.AGENT_PURPLE,
                command=lambda: self._on_navigate("agents"),
            ).pack(side="right")

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

        self._stages = PipelineStageStrip(self)
        self._stages.pack(fill="x", padx=T.PAD, pady=(0, 8))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        list_host = ctk.CTkFrame(
            body,
            fg_color=T.BG_PANEL,
            border_color=T.EXECUTION_BLUE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        list_host.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(
            list_host,
            text="Operations",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._ops_scroll = ctk.CTkScrollableFrame(
            list_host, fg_color=T.BG_DEEP, corner_radius=0
        )
        self._ops_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        right = ctk.CTkFrame(
            body,
            fg_color=T.BG_PANEL,
            border_color=T.EXECUTION_BLUE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        right.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(
            right,
            text="Live Timeline",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._dock = ExecutionTimelineDock(right, on_scrub=self._handle_scrub)
        self._dock.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_state(self, snapshot: AppState | None) -> None:
        if snapshot is None:
            set_surface_state(
                self._surface_state,
                kind="loading",
                message=article18_loading(
                    status="Status: loading Mission Control",
                    what="operation library, journal, and execution timeline",
                    next_action="Wait for AppState refresh; then scrub the timeline.",
                ),
            )
            return
        if not isinstance(snapshot, AppState):
            return
        self._last_snap = snapshot

        ops = list(snapshot.operation_library_index)
        active = snapshot.active_operation
        journal = tuple(snapshot.operation_journal)
        scrubber = snapshot.execution_scrubber
        pipeline = snapshot.agent_pipeline
        orch = snapshot.orchestration_run

        self._metrics.configure(
            text=f"{len(ops)} operations · {len(journal)} journal"
        )

        err = domain_error_from_snap(
            snapshot, topic_prefixes=("operation.", "orchestration.", "execution.")
        )
        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif not ops and not journal and not scrubber.events:
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="No operations or journal events are projected yet.",
                    creates="Operations appear when goals/pipelines complete and index.",
                    next_action="Run a goal or agent pipeline, then return here.",
                ),
            )
        else:
            set_surface_state(self._surface_state, kind="data")

        if active is not None and not self._selected_correlation_id:
            self._selected_correlation_id = active.correlation_id
        elif ops and not self._selected_correlation_id:
            self._selected_correlation_id = ops[0].correlation_id

        stage_idx = resolve_active_stage_index(
            pipeline_stage=pipeline.pipeline_stage,
            truth_valid=bool(orch.truth_valid),
            has_receipt=bool(orch.receipt_id),
        )
        detail = pipeline.pipeline_stage or (
            active.goal_title if active is not None else ""
        )
        self._stages.apply_active_index(stage_idx, detail=detail)
        self._hint.configure(
            text=(
                f"Active: {self._selected_correlation_id or '—'}"
                + (f" · pipeline {pipeline.pipeline_id}" if pipeline.pipeline_id else "")
            )
        )

        self._render_operations(ops, active)
        self._timeline_steps = journal_to_timeline_steps(journal)
        if not self._timeline_steps:
            self._timeline_steps = scrubber_events_to_steps(tuple(scrubber.events))
        self._scrub_index = int(getattr(scrubber, "scrub_index", 0) or 0)
        self._dock.render(self._timeline_steps, scrub_index=self._scrub_index)

    def _render_operations(
        self,
        ops: list[OperationSnapshot],
        active: OperationSnapshot | None,
    ) -> None:
        clear_children(self._ops_scroll)
        items = list(ops)
        if active is not None and all(
            o.correlation_id != active.correlation_id for o in items
        ):
            items.insert(0, active)
        if not items:
            ctk.CTkLabel(
                self._ops_scroll,
                text="No operations in the library yet.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=8, pady=12)
            return
        for op in items[:40]:
            OperationCard(
                self._ops_scroll,
                correlation_id=op.correlation_id,
                title=op.goal_title or op.correlation_id,
                status=op.goal_status or ("partial" if op.is_partial else "ready"),
                selected=op.correlation_id == self._selected_correlation_id,
                on_select=self._select_operation,
            ).pack(fill="x", pady=3)

    def _select_operation(self, correlation_id: str) -> None:
        cid = str(correlation_id).strip()
        self._selected_correlation_id = cid
        if self._on_select_operation is not None:
            self._on_select_operation(cid)
        if self._on_inspect_select is not None:
            self._on_inspect_select(
                InspectableRef(
                    kind="operation",
                    ref_id=cid,
                    label=cid,
                    payload=(
                        ("correlation_id", cid),
                        ("name", cid),
                        ("status", "selected"),
                    ),
                )
            )
        if self._last_snap is not None:
            self.apply_state(self._last_snap)

    def _handle_scrub(self, index: int) -> None:
        self._scrub_index = int(index)
        step: dict[str, object] = {}
        if self._timeline_steps:
            clamped = max(0, min(self._scrub_index, len(self._timeline_steps) - 1))
            step = dict(self._timeline_steps[clamped])
            self._scrub_index = clamped
        if self._on_scrub is not None:
            self._on_scrub(self._scrub_index, step)
        if self._on_inspect_select is not None:
            label = str(step.get("name") or f"step {self._scrub_index}")
            self._on_inspect_select(
                InspectableRef(
                    kind="execution_event",
                    ref_id=str(
                        step.get("event_id")
                        or step.get("entry_id")
                        or f"scrub-{self._scrub_index}"
                    ),
                    label=label,
                    payload=(
                        ("event_type", str(step.get("kind") or "timeline")),
                        ("status", str(step.get("status") or "")),
                        ("detail", label),
                        ("summary", label),
                        ("index", str(self._scrub_index)),
                        (
                            "correlation_id",
                            str(
                                step.get("correlation_id")
                                or self._selected_correlation_id
                            ),
                        ),
                    ),
                )
            )


__all__ = [
    "OperationsView",
    "journal_to_timeline_steps",
    "scrubber_events_to_steps",
]
