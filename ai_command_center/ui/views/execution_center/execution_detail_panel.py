"""Execution Detail — active_plan + execution_context projection."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import execution_state_color
from ai_command_center.ui.widget_utils import clear_children


class ExecutionDetailPanel(ctk.CTkFrame):
    """Read-only detail for the selected / active execution."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.EXECUTION_BLUE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Execution Detail",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(side="left")
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._empty()

    def apply_snapshot(self, snap: AppState, *, selected_request_id: str = "") -> None:
        plan = snap.execution_library.active_plan
        ctx = snap.execution_context
        rid = selected_request_id or plan.request_id or ctx.request_id
        matches_plan = bool(rid) and rid in {plan.request_id, plan.run_id}
        matches_ctx = bool(rid) and rid == ctx.request_id
        current = ""
        if matches_plan and plan.current_step is not None:
            current = plan.current_step.capability or plan.current_step.step_id
        goal = plan.goal if matches_plan else (ctx.query if matches_ctx else "")
        status = plan.status if matches_plan else (ctx.status if matches_ctx else "—")
        error = plan.error if matches_plan and plan.error else "none"
        fingerprint = (
            str(rid or ""),
            bool(matches_plan),
            bool(matches_ctx),
            str(goal or ""),
            str(status or ""),
            str(current or ""),
            str(error or ""),
            str(ctx.provider_id or "") if matches_ctx else "",
            str(ctx.model or "") if matches_ctx else "",
            str(ctx.status or "") if matches_ctx else "",
            str(ctx.intent or "") if matches_ctx else "",
        )
        if fingerprint == getattr(self, "_snapshot_fingerprint", None):
            return
        self._snapshot_fingerprint = fingerprint

        clear_children(self._body)
        if not rid:
            self._empty()
            return

        if not matches_plan and not matches_ctx:
            self._row("Request ID", rid)
            self._muted(
                "No detail available for this selection yet.\n"
                "Detail projects from the active plan or execution context for the request.\n"
                "Next: select a run that still has plan/context in AppState."
            )
            return

        fg, _ = execution_state_color(status)
        self._row("Request ID", rid)
        self._row("Goal", goal or "—")
        self._row("Status", status or "—", color=fg)
        self._row("Current Step", current or "—")
        self._row("Error State", error)
        if matches_ctx:
            self._row("Provider", str(ctx.provider_id or "—"))
            self._row("Model", str(ctx.model or "—"))
            self._row("Runtime Status", str(ctx.status or "—"))
            self._row("Intent", str(ctx.intent or "—"))

    def _empty(self) -> None:
        # Caller already cleared; avoid double-destroy on Python 3.14 CTk.
        self._muted(
            "No execution selected for detail.\n"
            "Detail appears when you select a run from the list or hero action.\n"
            "Next: select an execution in the list."
        )

    def _muted(self, text: str) -> None:
        ctk.CTkLabel(
            self._body, text=text, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=4, pady=12)

    def _row(self, label: str, value: str, *, color: str = T.TEXT_PRIMARY) -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(
            frame, text=label, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, width=110, anchor="w"
        ).pack(side="left")
        ctk.CTkLabel(
            frame, text=value, font=T.FONT_SMALL, text_color=color, anchor="w", wraplength=220
        ).pack(side="left", fill="x", expand=True)
