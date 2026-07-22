"""Receipt / facts / trace chain for Evidence Workspace (PR-UI-E10)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class ReceiptChain(ctk.CTkFrame):
    """Shows facts, receipt id, and trace identifiers for a selected claim."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.EXECUTION_BLUE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text="Facts · Receipt · Trace",
            font=T.FONT_HEADER,
            text_color=T.EXECUTION_BLUE,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(10, 4))
        self._body = ctk.CTkScrollableFrame(self, fg_color=T.BG_DEEP, corner_radius=0)
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_entry(self, entry: Any | None) -> None:
        clear_children(self._body)
        if entry is None:
            ctk.CTkLabel(
                self._body,
                text=(
                    "No claim selected.\n"
                    "Facts, receipt, and trace appear when an orchestration run "
                    "is selected from the evidence list.\n"
                    "Next: select a claim card."
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                justify="left",
            ).pack(fill="x", padx=4, pady=12)
            return

        facts = getattr(entry, "execution_facts", ()) or ()
        if isinstance(facts, dict):
            fact_pairs = tuple(facts.items())
        else:
            fact_pairs = tuple(facts)

        self._row("Receipt ID", str(getattr(entry, "receipt_id", "") or "—"))
        self._row("Trace ID", str(getattr(entry, "trace_id", "") or "—"))
        self._row("Span ID", str(getattr(entry, "span_id", "") or "—"))
        self._row(
            "Execution",
            "success" if getattr(entry, "execution_success", False) else "failed",
        )
        err = getattr(entry, "execution_error", None)
        if err:
            self._row("Error", str(err), color=T.STATUS_ERROR)

        ctk.CTkLabel(
            self._body,
            text="Facts",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(10, 2))
        if not fact_pairs:
            ctk.CTkLabel(
                self._body,
                text="No execution facts on this claim.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=4, pady=2)
            return
        for key, value in fact_pairs:
            self._row(str(key), str(value))

    def _row(self, label: str, value: str, *, color: str = T.TEXT_PRIMARY) -> None:
        frame = ctk.CTkFrame(self._body, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(
            frame,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=110,
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


__all__ = ["ReceiptChain"]
