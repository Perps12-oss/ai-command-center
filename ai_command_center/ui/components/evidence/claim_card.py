"""Claim card for Evidence Workspace list (PR-UI-E10)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.evidence.truth_badge import TruthBadge
from ai_command_center.ui.design_system import theme_v2 as T


class ClaimCard(ctk.CTkFrame):
    """One orchestration claim / run entry in the evidence list."""

    def __init__(
        self,
        master: Any,
        *,
        request_id: str,
        claim_text: str,
        truth_state: str = "",
        receipt_id: str = "",
        selected: bool = False,
        on_select: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.HERO_CYAN_DIM if selected else T.BG_GLASS,
            border_color=T.EXECUTION_BLUE if selected else T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        self._request_id = request_id
        self._on_select = on_select

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            top,
            text=claim_text[:96] or request_id or "Untitled claim",
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        badge = TruthBadge(top)
        badge.pack(side="right")
        badge.set_state(truth_state)

        meta = receipt_id or request_id
        ctk.CTkLabel(
            self,
            text=meta,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 8))
        self.bind("<Button-1>", self._click)

    def _click(self, _e: Any = None) -> None:
        if self._on_select is not None and self._request_id:
            self._on_select(self._request_id)


__all__ = ["ClaimCard"]
