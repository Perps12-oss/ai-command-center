"""Execution Timeline — steps + existing scrubber projection."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.ui.components.docks.execution_timeline_dock import ExecutionTimelineDock
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import execution_state_color
from ai_command_center.ui.widget_utils import clear_children


class ExecutionTimelinePanel(ctk.CTkFrame):
    """Timeline of execution steps with scrubber (existing publish path)."""

    def __init__(
        self,
        master: Any,
        *,
        on_scrub: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.EXECUTION_BLUE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        self._on_scrub = on_scrub
        self._request_id = ""

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Execution Timeline",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(side="left")
        self._summary = ctk.CTkLabel(
            header,
            text="0 steps",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._summary.pack(side="right")

        self._step_list = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, height=90, border_width=0
        )
        self._step_list.pack(fill="x", padx=8, pady=(0, 4))

        self._dock = ExecutionTimelineDock(
            self,
            on_scrub=self._handle_scrub,
            timeline_height=72,
            show_section_labels=False,
        )
        self._dock.pack(fill="x", padx=4, pady=(0, 8))

    def apply_snapshot(self, snap: AppState, *, selected_request_id: str = "") -> None:
        self._request_id = selected_request_id or snap.execution_scrubber.request_id
        plan = snap.execution_library.active_plan
        steps = list(plan.steps) if (
            plan.request_id == self._request_id or plan.run_id == self._request_id
        ) else []

        scrub = snap.execution_scrubber
        timeline_steps: list[dict[str, Any]] = []
        labels: list[str] = []
        if scrub.request_id == self._request_id and scrub.events:
            for event in scrub.events:
                labels.append(event.event_type)
                timeline_steps.append(
                    {
                        "name": event.scope or event.event_type.split(".")[-1] or event.event_type,
                        "status": "ok",
                        "duration_ms": 0.0,
                        "detail": dict(event.payload),
                    }
                )
        elif steps:
            for step in steps:
                labels.append(step.capability or step.step_id)
                timeline_steps.append(
                    {
                        "name": step.capability or step.step_id or f"step-{step.index}",
                        "status": step.status,
                        "duration_ms": 0.0,
                        "detail": {"error": step.error, "risk": step.risk},
                    }
                )

        clear_children(self._step_list)
        if not steps and not timeline_steps:
            ctk.CTkLabel(
                self._step_list,
                text="Select an execution to view timeline.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=12)
            self._summary.configure(text="0 steps")
            self._dock.render([], scrub_labels=[], scrub_index=0)
            return

        counts = {"completed": 0, "failed": 0, "waiting": 0, "current": 0}
        display_steps = steps or [
            type(
                "S",
                (),
                {
                    "step_id": "",
                    "status": s.get("status", ""),
                    "capability": s.get("name", ""),
                    "error": "",
                },
            )()
            for s in timeline_steps
        ]
        current_id = plan.current_step_id if steps else ""
        for step in display_steps:
            status = str(getattr(step, "status", "") or "")
            is_current = getattr(step, "step_id", "") == current_id and bool(current_id)
            if is_current:
                counts["current"] += 1
            if status in {"completed", "complete", "ok", "success"}:
                counts["completed"] += 1
            elif status in {"failed", "error"}:
                counts["failed"] += 1
            elif status in {"waiting", "pending", "queued", "awaiting_approval"}:
                counts["waiting"] += 1
            fg, _ = execution_state_color(status or ("running" if is_current else "idle"))
            label = getattr(step, "capability", None) or getattr(step, "step_id", "") or "step"
            prefix = "▶ " if is_current else "• "
            ctk.CTkLabel(
                self._step_list,
                text=f"{prefix}{label}  [{status or '—'}]",
                font=T.FONT_SMALL,
                text_color=fg,
                anchor="w",
            ).pack(fill="x", padx=4, pady=1)

        self._summary.configure(
            text=(
                f"{len(display_steps)} steps · "
                f"{counts['current']} current · "
                f"{counts['completed']} done · "
                f"{counts['failed']} failed · "
                f"{counts['waiting']} waiting"
            )
        )
        scrub_index = (
            scrub.scrub_index
            if scrub.request_id == self._request_id
            else max(0, len(timeline_steps) - 1)
        )
        self._dock.render(
            timeline_steps,
            scrub_labels=labels,
            scrub_index=scrub_index,
        )

    def apply_timeline(
        self,
        *,
        request_id: str,
        timeline_steps: Sequence[dict[str, Any]],
        scrub_labels: Sequence[str],
        scrub_index: int,
        timeline_source: str,
    ) -> None:
        """Compatibility path used by StateApplier scrubber projection."""
        del timeline_source
        self._request_id = request_id
        self._dock.render(
            list(timeline_steps),
            scrub_labels=list(scrub_labels),
            scrub_index=scrub_index,
        )
        self._summary.configure(text=f"{len(timeline_steps)} timeline events")

    def _handle_scrub(self, index: int) -> None:
        if self._on_scrub:
            self._on_scrub(index)
