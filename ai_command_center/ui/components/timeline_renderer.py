"""TimelineRenderer — horizontal timeline of execution steps.

Used by ExecutionDetailView. Renders a sequence of step tiles with
status indicators and durations.

Architecture contract: pure display widget, no bus/service imports.
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import execution_state_color


class _StepTile(ctk.CTkFrame):
    """A single step tile in the timeline."""

    def __init__(
        self,
        master: Any,
        index: int,
        name: str,
        status: str,
        duration_ms: float = 0,
        active: bool = False,
    ) -> None:
        color = execution_state_color(status)[0]
        bg = T.BG_GLASS if active else T.BG_PANEL
        super().__init__(
            master,
            fg_color=bg,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=color,
            width=100,
        )
        self.pack_propagate(False)

        ctk.CTkLabel(
            self,
            text=str(index + 1),
            font=(T.FONT_FAMILY, 9),
            text_color=color,
            width=20,
        ).pack(pady=(4, 0))

        ctk.CTkLabel(
            self,
            text=name[:14],
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_PRIMARY if active else T.TEXT_SECONDARY,
            wraplength=88,
            justify="center",
        ).pack(padx=4)

        if duration_ms:
            ctk.CTkLabel(
                self,
                text=f"{duration_ms / 1000:.1f}s",
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
            ).pack(pady=(0, 4))


class TimelineRenderer(ctk.CTkFrame):
    """Horizontal scrollable timeline of execution steps.

    ┌───────┐ → ┌───────┐ → ┌───────┐
    │ step1 │   │ step2 │   │ step3 │
    └───────┘   └───────┘   └───────┘
    """

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)

        self._scroll = ctk.CTkScrollableFrame(
            self,
            orientation="horizontal",
            fg_color="transparent",
            height=90,
            corner_radius=0,
        )
        self._scroll.pack(fill="x", padx=4, pady=4)

    def render(
        self,
        steps: list[dict],
        *,
        active_index: int = -1,
    ) -> None:
        """Render steps. Each step: {name, status, duration_ms}."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not steps:
            ctk.CTkLabel(
                self._scroll,
                text="No steps",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(padx=20, pady=30)
            return

        for i, step in enumerate(steps):
            _StepTile(
                self._scroll,
                index=i,
                name=str(step.get("name", f"Step {i+1}")),
                status=str(step.get("status", "pending")),
                duration_ms=float(step.get("duration_ms", 0)),
                active=(i == active_index),
            ).pack(side="left", padx=(4, 0), pady=4)

            # Arrow connector
            if i < len(steps) - 1:
                ctk.CTkLabel(
                    self._scroll,
                    text="→",
                    font=(T.FONT_FAMILY, 12),
                    text_color=T.TEXT_MUTED,
                    width=16,
                ).pack(side="left", pady=4)
