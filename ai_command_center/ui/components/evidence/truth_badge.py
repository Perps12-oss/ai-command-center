"""Truth status badge for Evidence Workspace (PR-UI-E10)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import truth_validation_color


class TruthBadge(ctk.CTkLabel):
    """Compact truth status chip (valid | partial | failed | —)."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            text="—",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            padx=8,
            pady=2,
            **kwargs,
        )

    def set_state(self, state: str) -> None:
        key = str(state or "").strip().lower()
        if not key:
            self.configure(text="—", text_color=T.TEXT_MUTED, fg_color=T.BG_GLASS)
            return
        fg, bg = truth_validation_color(key)
        self.configure(text=key.upper(), text_color=fg, fg_color=bg)


__all__ = ["TruthBadge"]
