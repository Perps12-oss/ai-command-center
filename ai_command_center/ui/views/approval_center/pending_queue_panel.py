"""Pending Queue — primary Approval Center surface."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.execution_library_snapshot import ExecutionLibrarySnapshot
from ai_command_center.domain.permission_check_snapshot import (
    PendingCheck,
    PermissionCheckSnapshot,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color
from ai_command_center.ui.views.approval_center.risk_classification import (
    classify_approval_risk,
)
from ai_command_center.ui.widget_utils import clear_children


class PendingQueuePanel(ctk.CTkFrame):
    """Dominant pending approval surface with Approve / Deny intents."""

    def __init__(
        self,
        master: Any,
        *,
        on_approve: Callable[[PendingCheck], None] | None = None,
        on_deny: Callable[[PendingCheck], None] | None = None,
        on_select: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.APPROVAL_ORANGE,
            border_width=2,
            corner_radius=T.CORNER_RADIUS,
        )
        self._on_approve = on_approve
        self._on_deny = on_deny
        self._on_select = on_select
        self._pending: PendingCheck | None = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(12, 4))
        ctk.CTkLabel(
            header,
            text="Pending Queue",
            font=T.FONT_TITLE,
            text_color=T.APPROVAL_ORANGE,
            anchor="w",
        ).pack(side="left")
        self._badge = ctk.CTkLabel(
            header,
            text="0 pending",
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._badge.pack(side="right")

        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=T.PAD, pady=(0, 12))
        self._approve_btn = ctk.CTkButton(
            actions,
            text="Approve",
            font=T.FONT_BODY,
            fg_color=T.STATUS_READY,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            height=30,
            width=110,
            state="disabled",
            command=self._approve,
        )
        self._approve_btn.pack(side="left", padx=(0, 8))
        self._deny_btn = ctk.CTkButton(
            actions,
            text="Deny",
            font=T.FONT_BODY,
            fg_color=T.STATUS_ERROR,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            height=30,
            width=110,
            state="disabled",
            command=self._deny,
        )
        self._deny_btn.pack(side="left")

    def apply_snapshot(
        self,
        permission: PermissionCheckSnapshot,
        *,
        execution_library: ExecutionLibrarySnapshot | None = None,
        focused_check_id: str = "",
    ) -> None:
        pending = permission.pending
        self._pending = pending
        clear_children(self._body)
        if pending is None:
            self._badge.configure(text="0 pending", text_color=T.TEXT_MUTED)
            self._approve_btn.configure(state="disabled")
            self._deny_btn.configure(state="disabled")
            ctk.CTkLabel(
                self._body,
                text=(
                    "No pending approvals.\n"
                    "Interactive permission checks appear when an agent or "
                    "execution step requests supervised authorization.\n"
                    "Next: run a supervised agent or execution that requires approval."
                ),
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=6, pady=16)
            return

        focused = not focused_check_id or focused_check_id == pending.check_id
        self._badge.configure(text="1 pending", text_color=T.APPROVAL_ORANGE)
        self._approve_btn.configure(state="normal" if focused else "disabled")
        self._deny_btn.configure(state="normal" if focused else "disabled")

        risk = classify_approval_risk(pending, execution_library=execution_library)
        risk_fg = status_color(
            "error" if risk.tier in {"high", "critical"} else (
                "busy" if risk.tier == "medium" else "ready"
            )
        )
        if risk.tier == "unknown":
            risk_fg = T.TEXT_MUTED

        card = ctk.CTkFrame(
            self._body,
            fg_color=T.BG_GLASS,
            border_color=T.APPROVAL_ORANGE if focused else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        card.pack(fill="x", pady=4)
        self._row(card, "Check ID", pending.check_id or "—")
        self._row(card, "Summary", pending.summary or "—")
        self._row(
            card,
            "Actor",
            f"{pending.actor_type or 'agent'} · {pending.actor_id or '—'}",
        )
        perms = ", ".join(pending.permissions) if pending.permissions else "—"
        self._row(card, "Requested Permission", perms)
        self._row(card, "Risk Indicator", risk.tier.upper(), color=risk_fg)

        def _select(_e: Any = None) -> None:
            if self._on_select:
                self._on_select(pending.check_id)

        card.bind("<Button-1>", _select)

    def _row(
        self, parent: Any, label: str, value: str, *, color: str = T.TEXT_PRIMARY
    ) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(
            row,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=140,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            row,
            text=value,
            font=T.FONT_BODY,
            text_color=color,
            anchor="w",
            wraplength=420,
            justify="left",
        ).pack(side="left", fill="x", expand=True)

    def _approve(self) -> None:
        if self._pending and self._on_approve:
            self._on_approve(self._pending)

    def _deny(self) -> None:
        if self._pending and self._on_deny:
            self._on_deny(self._pending)
