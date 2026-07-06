"""ResponseActionStrip — Open WebUI–style action bar below assistant messages.

Shows: Execution #N | N Artifacts | N Decisions
Tapping any pill opens the inspector on the relevant tab.

Architecture contract: pure display widget, no bus/service imports.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class _ActionPill(ctk.CTkButton):
    """Small pill button for the action strip."""

    def __init__(
        self,
        master: Any,
        text: str,
        on_click: Callable[[], None],
        count: int = 0,
    ) -> None:
        label = f"{text}  {count}" if count else text
        super().__init__(
            master,
            text=label,
            height=22,
            font=(T.FONT_FAMILY, 10),
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
            command=on_click,
        )


class ResponseActionStrip(ctk.CTkFrame):
    """Horizontal strip of action pills below an assistant message.

    ┌────────────────────────────────────────────────────────┐
    │  ⚡ Execution #3  │  📄 2 Artifacts  │  ✓ 1 Decision  │
    └────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        *,
        execution_id: str = "",
        execution_index: int = 0,
        artifact_count: int = 0,
        decision_count: int = 0,
        on_open_inspector: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_open_inspector = on_open_inspector or (lambda tab: None)

        if execution_id or execution_index:
            label = f"⚡ Execution #{execution_index}" if execution_index else "⚡ Execution"
            _ActionPill(
                self, label, lambda: self._on_open_inspector("Trace")
            ).pack(side="left", padx=(0, 4))

        if artifact_count:
            _ActionPill(
                self,
                "📄 Artifacts",
                lambda: self._on_open_inspector("Artifacts"),
                count=artifact_count,
            ).pack(side="left", padx=(0, 4))

        if decision_count:
            _ActionPill(
                self,
                "✓ Decisions",
                lambda: self._on_open_inspector("Trace"),
                count=decision_count,
            ).pack(side="left", padx=(0, 4))
