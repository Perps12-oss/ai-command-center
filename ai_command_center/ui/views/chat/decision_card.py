"""DecisionCard — inline approval/decision card for supervised agent flows.

Shown when the orchestration layer emits a pending decision that requires
user confirmation before proceeding.

Architecture contract: pure display widget, no bus/service imports.
on_approve / on_reject callbacks route through UIController → EventBus.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class DecisionCard(ctk.CTkFrame):
    """Inline decision card requesting user approval.

    ┌────────────────────────────────────────────────────────┐
    │ ⚠  Decision required                                   │
    │ The agent wants to: <summary>                          │
    │                             [Approve]  [Reject]        │
    └────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        decision_id: str,
        summary: str,
        *,
        on_approve: Callable[[str], None] | None = None,
        on_reject: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.STATUS_BUSY_BG,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=T.STATUS_BUSY,
            **kwargs,
        )
        self._decision_id = decision_id
        self._on_approve = on_approve or (lambda d: None)
        self._on_reject = on_reject or (lambda d: None)
        self._resolved = False

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            header,
            text="⚠  Decision required",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.STATUS_BUSY,
        ).pack(side="left")

        # Summary
        ctk.CTkLabel(
            self,
            text=summary[:200],
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            wraplength=400,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkFrame(btn_row, fg_color="transparent").pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(
            btn_row,
            text="Approve",
            width=80, height=28,
            font=(T.FONT_FAMILY, 11),
            fg_color=T.STATUS_READY,
            hover_color="#16A34A",
            text_color="#FFFFFF",
            corner_radius=T.SMALL_RADIUS,
            command=self._approve,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_row,
            text="Reject",
            width=80, height=28,
            font=(T.FONT_FAMILY, 11),
            fg_color=T.BG_GLASS,
            hover_color=T.STATUS_ERROR_BG,
            text_color=T.TEXT_SECONDARY,
            corner_radius=T.SMALL_RADIUS,
            command=self._reject,
        ).pack(side="left")

    def _approve(self) -> None:
        if not self._resolved:
            self._resolved = True
            self._on_approve(self._decision_id)
            self._show_resolved("Approved ✓", T.STATUS_READY)

    def _reject(self) -> None:
        if not self._resolved:
            self._resolved = True
            self._on_reject(self._decision_id)
            self._show_resolved("Rejected ✕", T.STATUS_ERROR)

    def _show_resolved(self, text: str, color: str) -> None:
        for child in self.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self,
            text=text,
            font=(T.FONT_FAMILY, 11),
            text_color=color,
        ).pack(pady=8)
        self.configure(
            fg_color=T.BG_GLASS,
            border_color=color,
        )
