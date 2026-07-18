"""Approval Statistics — informational counters only."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.permission_check_snapshot import PermissionCheckSnapshot
from ai_command_center.ui.design_system import theme_v2 as T


class ApprovalStatisticsPanel(ctk.CTkFrame):
    """Visual summary of projected permission totals (below pending queue)."""

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
            text="Approval Statistics",
            font=T.FONT_HEADER,
            text_color=T.APPROVAL_ORANGE,
            anchor="w",
        ).pack(side="left")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=T.PAD, pady=(4, T.PAD))
        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

        self._requested = self._metric(grid, 0, 0, "Total Requested")
        self._granted = self._metric(grid, 0, 1, "Total Granted")
        self._denied = self._metric(grid, 1, 0, "Total Denied")
        self._pending = self._metric(grid, 1, 1, "Pending Count")

    def _metric(
        self, parent: Any, row: int, col: int, label: str
    ) -> ctk.CTkLabel:
        cell = ctk.CTkFrame(
            parent,
            fg_color=T.BG_DEEP,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        cell.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        ctk.CTkLabel(
            cell,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 0))
        value = ctk.CTkLabel(
            cell,
            text="0",
            font=T.FONT_TITLE,
            text_color=T.APPROVAL_ORANGE,
            anchor="w",
        )
        value.pack(fill="x", padx=8, pady=(0, 8))
        return value

    def apply_snapshot(self, permission: PermissionCheckSnapshot) -> None:
        pending_n = 1 if permission.has_pending else 0
        self._requested.configure(text=str(permission.total_requested))
        self._granted.configure(text=str(permission.total_granted))
        self._denied.configure(text=str(permission.total_denied))
        self._pending.configure(text=str(pending_n))
