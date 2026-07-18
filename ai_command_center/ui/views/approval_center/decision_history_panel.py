"""Decision History — projected resolved checks only."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.permission_check_snapshot import PermissionCheckSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color
from ai_command_center.ui.widget_utils import clear_children


class DecisionHistoryPanel(ctk.CTkFrame):
    """Operational decision history from permission_snapshot.resolved."""

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.APPROVAL_ORANGE,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Decision History",
            font=T.FONT_HEADER,
            text_color=T.APPROVAL_ORANGE,
            anchor="w",
        ).pack(side="left")
        self._count = ctk.CTkLabel(
            header,
            text="0",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._count.pack(side="right")
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=T.BG_DEEP, border_width=0, corner_radius=T.SMALL_RADIUS
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(self, permission: PermissionCheckSnapshot) -> None:
        resolved = list(permission.resolved)
        self._count.configure(text=str(len(resolved)))
        clear_children(self._body)
        if not resolved:
            ctk.CTkLabel(
                self._body,
                text=(
                    "No decisions recorded yet.\n"
                    "Resolved approvals and denials appear after Approve/Deny on a pending check.\n"
                    "Next: use Review Next when a supervised check is pending."
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=4, pady=12)
            return

        for item in resolved:
            outcome = "granted" if item.granted else "denied"
            fg = status_color("ready" if item.granted else "error")
            row = ctk.CTkFrame(
                self._body,
                fg_color="transparent",
                border_color=T.BG_GLASS_BORDER,
                border_width=1,
                corner_radius=T.SMALL_RADIUS,
            )
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row,
                text=f"{outcome.upper()} · {item.actor_id or '—'} · {item.check_id or '—'}",
                font=T.FONT_SMALL,
                text_color=fg,
                anchor="w",
            ).pack(fill="x", padx=8, pady=(4, 0))
            ctk.CTkLabel(
                row,
                text=item.summary or "—",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                wraplength=320,
                justify="left",
            ).pack(fill="x", padx=8, pady=(0, 4))
