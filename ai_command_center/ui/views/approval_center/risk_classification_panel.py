"""Risk Classification — explicit tier, reason, and source."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.execution_library_snapshot import ExecutionLibrarySnapshot
from ai_command_center.domain.permission_check_snapshot import PermissionCheckSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color
from ai_command_center.ui.views.approval_center.risk_classification import (
    classify_approval_risk,
)
from ai_command_center.ui.widget_utils import clear_children


class RiskClassificationPanel(ctk.CTkFrame):
    """Shows why a risk tier was chosen — never a badge alone."""

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
            text="Risk Classification",
            font=T.FONT_HEADER,
            text_color=T.APPROVAL_ORANGE,
            anchor="w",
        ).pack(side="left")
        self._body = ctk.CTkFrame(self, fg_color=T.BG_DEEP, corner_radius=T.SMALL_RADIUS)
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(
        self,
        permission: PermissionCheckSnapshot,
        *,
        execution_library: ExecutionLibrarySnapshot | None = None,
    ) -> None:
        clear_children(self._body)
        view = classify_approval_risk(
            permission.pending, execution_library=execution_library
        )
        tier_fg = status_color(
            "error" if view.tier in {"high", "critical"} else (
                "busy" if view.tier == "medium" else (
                    "ready" if view.tier == "low" else "offline"
                )
            )
        )
        self._row("Risk Tier", view.tier.upper(), color=tier_fg)
        self._row("Risk Reason", view.reason, color=T.TEXT_PRIMARY)
        self._row("Source", view.source, color=T.TEXT_SECONDARY)

    def _row(self, label: str, value: str, *, color: str = T.TEXT_PRIMARY) -> None:
        row = ctk.CTkFrame(self._body, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(
            row,
            text=label,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=110,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            row,
            text=value,
            font=T.FONT_BODY,
            text_color=color,
            anchor="w",
            wraplength=280,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
