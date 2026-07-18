"""ToolExecutionCard — Langflow-style inline tool execution card.

Displayed inline in the message feed when a tool is invoked or completes.

Architecture contract: pure display widget, no bus/service imports.
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import execution_state_color

_STATUS_ICONS: dict[str, str] = {
    "running":   "⟳",
    "success":   "✓",
    "failed":    "✕",
    "error":     "✕",
    "cancelled": "–",
    "pending":   "○",
}


class ToolExecutionCard(ctk.CTkFrame):
    """Inline card showing a tool execution with status, output, and duration.

    ┌─────────────────────────────────────────┐
    │ ⟳  tool_name                 0.8s  ···  │
    │ ▾ input / output (collapsed)            │
    └─────────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        tool_name: str,
        *,
        status: str = "running",
        input_text: str = "",
        output_text: str = "",
        duration_ms: int = 0,
        **kwargs: Any,
    ) -> None:
        color = execution_state_color(status)[0]
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=color,
            **kwargs,
        )
        self._expanded = False
        self._output_text = output_text
        self._input_text = input_text

        self._build_header(tool_name, status, duration_ms, color)
        if output_text or input_text:
            self._build_detail()

    def _build_header(
        self, tool_name: str, status: str, duration_ms: int, color: str
    ) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=6)

        icon = _STATUS_ICONS.get(status, "○")
        ctk.CTkLabel(
            header,
            text=icon,
            font=(T.FONT_FAMILY, 11),
            text_color=color,
            width=16,
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=tool_name,
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=(4, 0), fill="x", expand=True)

        if duration_ms:
            ctk.CTkLabel(
                header,
                text=f"{duration_ms / 1000:.1f}s",
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
            ).pack(side="right", padx=4)

        if self._output_text or self._input_text:
            self._toggle_btn = ctk.CTkButton(
                header,
                text="▾",
                width=20, height=18,
                font=(T.FONT_FAMILY, 9),
                fg_color="transparent",
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.TEXT_MUTED,
                corner_radius=4,
                command=self._toggle,
            )
            self._toggle_btn.pack(side="right")

    def _build_detail(self) -> None:
        self._detail_frame = ctk.CTkFrame(self, fg_color=T.BG_INPUT, corner_radius=4)

        if self._input_text:
            ctk.CTkLabel(
                self._detail_frame,
                text="INPUT",
                font=(T.FONT_FAMILY, 8),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(padx=8, pady=(4, 0), anchor="w")
            ctk.CTkLabel(
                self._detail_frame,
                text=self._input_text[:200],
                font=("Consolas", 10),
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=280,
            ).pack(padx=8, pady=(0, 4), anchor="w")

        if self._output_text:
            ctk.CTkLabel(
                self._detail_frame,
                text="OUTPUT",
                font=(T.FONT_FAMILY, 8),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(padx=8, pady=(4, 0), anchor="w")
            ctk.CTkLabel(
                self._detail_frame,
                text=self._output_text[:300],
                font=("Consolas", 10),
                text_color=T.CODE_TEXT,
                anchor="w",
                justify="left",
                wraplength=280,
            ).pack(padx=8, pady=(0, 6), anchor="w")

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self._detail_frame.pack(fill="x", padx=6, pady=(0, 6))
            self._toggle_btn.configure(text="▴")
        else:
            self._detail_frame.pack_forget()
            self._toggle_btn.configure(text="▾")

    def update_status(self, status: str, output_text: str = "") -> None:
        """Update running → success/failed after completion."""
        color = execution_state_color(status)[0]
        self.configure(border_color=color)
        if output_text:
            self._output_text = output_text
