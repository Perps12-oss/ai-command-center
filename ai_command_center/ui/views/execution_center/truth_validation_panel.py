"""Truth Validation — verified-or-not projection of orchestration_run."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import truth_validation_color
from ai_command_center.ui.views.execution_center.receipt_viewer_panel import (
    resolve_orchestration_entry,
)
from ai_command_center.ui.widget_utils import clear_children


def truth_state_for_entry(entry: Any) -> str:
    """Map orchestration truth fields to valid | partial | failed."""
    if entry is None:
        return ""
    detail = str(getattr(entry, "truth_detail", "") or "").lower()
    if bool(getattr(entry, "truth_valid", False)):
        return "valid"
    if "partial" in detail or "degraded" in detail or "incomplete" in detail:
        return "partial"
    # Entry present but not verified → failed (do not invent success).
    return "failed"


class TruthValidationPanel(ctk.CTkFrame):
    """Was it verified? Separate from Receipt Viewer (what happened)."""

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
            text="Truth Validation",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(side="left")
        self._badge = ctk.CTkLabel(
            header,
            text="—",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._badge.pack(side="right")

        self._body = ctk.CTkFrame(self, fg_color=T.BG_DEEP, corner_radius=T.SMALL_RADIUS)
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._show_empty()

    def apply_snapshot(self, snap: AppState, *, selected_request_id: str = "") -> None:
        # Source of truth for verification is orchestration_run only (not receipts model).
        entry = resolve_orchestration_entry(
            snap.orchestration_run, selected_request_id=selected_request_id
        )
        state = truth_state_for_entry(entry)
        detail = str(getattr(entry, "truth_detail", "") or "") if entry is not None else ""
        source = str(getattr(entry, "response_source", "") or "") if entry is not None else ""

        clear_children(self._body)
        if not state:
            self._show_empty()
            return

        fg, bg = truth_validation_color(state)
        self._badge.configure(text=state.upper(), text_color=fg)
        self.configure(border_color=fg)

        self._row("Truth Valid", "yes" if state == "valid" else "no")
        self._row("Truth Source", source or "—")
        self._row("Validation Status", state, color=fg)
        self._row("Verification Notes", detail or "—")

        strip = ctk.CTkFrame(self._body, fg_color=bg, height=6, corner_radius=3)
        strip.pack(fill="x", padx=8, pady=(8, 4))

    def _show_empty(self) -> None:
        clear_children(self._body)
        self._badge.configure(text="—", text_color=T.TEXT_MUTED)
        self.configure(border_color=T.EXECUTION_BLUE)
        ctk.CTkLabel(
            self._body,
            text=(
                "No truth validation for this execution.\n"
                "Validation appears when an orchestration run records truth results.\n"
                "Next: select a run that completed truth validation."
            ),
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            justify="left",
        ).pack(pady=20)

    def _row(self, label: str, value: str, *, color: str = T.TEXT_PRIMARY) -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(
            frame, text=label, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, width=130, anchor="w"
        ).pack(side="left")
        ctk.CTkLabel(
            frame, text=value, font=T.FONT_SMALL, text_color=color, anchor="w", wraplength=220
        ).pack(side="left", fill="x", expand=True)
