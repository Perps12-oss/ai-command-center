"""Receipt Viewer — visualization of orchestration_run only."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.orchestration_run_snapshot import (
    OrchestrationRunEntry,
    OrchestrationRunSnapshot,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


def resolve_orchestration_entry(
    orch: OrchestrationRunSnapshot,
    *,
    selected_request_id: str = "",
) -> OrchestrationRunSnapshot | OrchestrationRunEntry | None:
    """Pick orchestration_run current or matching history entry. Never invent data."""
    rid = str(selected_request_id or "").strip()
    if rid:
        if orch.request_id == rid:
            return orch
        for entry in orch.run_history:
            if entry.request_id == rid:
                return entry
        return None
    if orch.request_id or orch.receipt_id:
        return orch
    if orch.run_history:
        return orch.run_history[0]
    return None


class ReceiptViewerPanel(ctk.CTkFrame):
    """Shows receipt evidence from orchestration_run. Empty when none exists."""

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
            text="Receipt Viewer",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(side="left")
        self._body = ctk.CTkFrame(self, fg_color=T.BG_DEEP, corner_radius=T.SMALL_RADIUS)
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._show_empty()

    def apply_snapshot(self, snap: AppState, *, selected_request_id: str = "") -> None:
        entry = resolve_orchestration_entry(
            snap.orchestration_run, selected_request_id=selected_request_id
        )
        clear_children(self._body)
        if entry is None or not getattr(entry, "receipt_id", ""):
            self._show_empty()
            return

        facts = getattr(entry, "execution_facts", ()) or ()
        if isinstance(facts, dict):
            fact_pairs = tuple(facts.items())
        else:
            fact_pairs = tuple(facts)
        summary = ", ".join(f"{k}={v}" for k, v in fact_pairs[:6]) if fact_pairs else "—"
        outcome = "success" if getattr(entry, "execution_success", False) else "failed"
        if getattr(entry, "execution_error", None):
            outcome = f"{outcome} ({entry.execution_error})"

        self._row("Receipt ID", str(entry.receipt_id))
        self._row("Response Source", str(getattr(entry, "response_source", "") or "—"))
        self._row("Execution Outcome", outcome)
        self._row("Evidence Summary", summary)

    def _show_empty(self) -> None:
        clear_children(self._body)
        ctk.CTkLabel(
            self._body,
            text="No receipt for this execution.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(pady=20)

    def _row(self, label: str, value: str) -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(
            frame, text=label, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, width=130, anchor="w"
        ).pack(side="left")
        ctk.CTkLabel(
            frame,
            text=value,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=220,
        ).pack(side="left", fill="x", expand=True)
