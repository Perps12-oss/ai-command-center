"""InspectorMetricsTab — execution metrics / KPI cards for the inspector panel.

Architecture contract: pure display widget, data supplied via update().
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class _MetricCard(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        label: str,
        value: str,
        color: str = T.TEXT_SECONDARY,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
        )
        ctk.CTkLabel(
            self,
            text=label,
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(padx=8, pady=(6, 0), anchor="w")
        ctk.CTkLabel(
            self,
            text=value,
            font=(T.FONT_FAMILY, 14, "bold"),
            text_color=color,
            anchor="w",
        ).pack(padx=8, pady=(2, 6), anchor="w")


class InspectorMetricsTab(ctk.CTkFrame):
    """Shows KPI metric cards for the current execution context."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._grid = ctk.CTkFrame(self, fg_color="transparent")
        self._grid.pack(fill="both", expand=True, padx=6, pady=6)
        self._grid.columnconfigure(0, weight=1)
        self._grid.columnconfigure(1, weight=1)

    def update(self, metrics: dict[str, Any]) -> None:
        """Refresh metric cards from a flat metrics dict."""
        for child in self._grid.winfo_children():
            child.destroy()

        if not metrics:
            ctk.CTkLabel(
                self._grid,
                text="No metrics",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).grid(row=0, column=0, columnspan=2, pady=20)
            return

        row = 0
        for col, (key, val) in enumerate(metrics.items()):
            if col > 0 and col % 2 == 0:
                row += 1
            display_val = str(val)
            if isinstance(val, float):
                display_val = f"{val:.3f}"
            elif isinstance(val, int):
                display_val = f"{val:,}"

            color = T.TEXT_PRIMARY
            if isinstance(val, (int, float)):
                if val == 0:
                    color = T.TEXT_MUTED
                elif val < 0:
                    color = T.STATUS_ERROR

            _MetricCard(
                self._grid,
                label=key.replace("_", " ").title(),
                value=display_val,
                color=color,
            ).grid(
                row=row,
                column=col % 2,
                padx=3, pady=3,
                sticky="ew",
            )
