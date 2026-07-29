"""State-aware KPI card — Tier 2/3 metrics with health, trend, freshness."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color


class StateAwareKpiCard(ctk.CTkFrame):
    """KPI card: icon + title, primary metric lines, trend, freshness, health."""

    def __init__(
        self,
        master,
        title: str,
        accent: str,
        command: Callable[[], None] | None = None,
        *,
        compact: bool = False,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.GLASS_BORDER,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
        )
        self._command = command
        self._accent = accent
        self._compact = compact
        self._fresh = True

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(10 if not compact else 6, 2))

        self._title = ctk.CTkLabel(
            top,
            text=title.upper(),
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._title.pack(side="left")

        self._health = ctk.CTkLabel(
            top,
            text="●",
            font=T.FONT_SMALL,
            text_color=T.STATUS_READY,
        )
        self._health.pack(side="right")

        self._metric = ctk.CTkLabel(
            self,
            text="—",
            font=(T.FONT_FAMILY, 22 if not compact else 16, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._metric.pack(fill="x", padx=T.PAD, pady=(0, 2))

        self._detail = ctk.CTkLabel(
            self,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._detail.pack(fill="x", padx=T.PAD, pady=(0, 2))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=T.PAD, pady=(0, 10 if not compact else 6))

        self._trend = ctk.CTkLabel(
            footer,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._trend.pack(side="left")

        self._freshness = ctk.CTkLabel(
            footer,
            text="Updated —",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._freshness.pack(side="right")

        # Compatibility aliases used by existing Command Center tests
        self._status = self._health
        self._sub = self._detail
        self._updated = self._freshness

        if command is not None:
            self.configure(cursor="hand2")
            self.bind("<Button-1>", lambda _e: self._on_click())
            for child in self.winfo_children():
                for widget in self._iter_bindable(child):
                    widget.bind("<Button-1>", lambda _e: self._on_click())

    def _iter_bindable(self, widget: Any):
        yield widget
        try:
            for child in widget.winfo_children():
                yield from self._iter_bindable(child)
        except Exception:
            return

    def _on_click(self) -> None:
        if self._command is not None:
            self._command()

    def update(
        self,
        metric: str,
        status: str,
        sub: str,
        timestamp: float,
        *,
        trend: str = "",
        stale_after: float = 300.0,
    ) -> None:
        """Update metric lines. Stale data is visually demoted."""
        now = time.time()
        age = (now - timestamp) if timestamp > 0 else 9999.0
        self._fresh = age <= stale_after

        metric_color = self._accent if self._fresh else T.TEXT_MUTED
        detail_color = T.TEXT_SECONDARY if self._fresh else T.TEXT_MUTED

        self._metric.configure(text=metric or "—", text_color=metric_color)
        self._detail.configure(text=sub or "", text_color=detail_color)
        status_text = (status or "ready").strip().lower()
        self._health.configure(
            text="●",
            text_color=status_color(status_text),
        )
        # Keep text status accessible (not color-only) via tooltip-like title attr
        self._status.configure(text=status_text)
        if trend:
            arrow = "▲" if trend.startswith("+") or "up" in trend.lower() else (
                "▼" if trend.startswith("-") or "down" in trend.lower() else "·"
            )
            self._trend.configure(
                text=f"{arrow} {trend}",
                text_color=T.STATUS_READY if arrow == "▲" else (
                    T.STATUS_ERROR if arrow == "▼" else T.TEXT_MUTED
                ),
            )
        else:
            self._trend.configure(text="")
        self._freshness.configure(
            text=f"Updated {_format_relative(timestamp)}"
            + ("" if self._fresh else " · stale"),
            text_color=T.TEXT_MUTED if self._fresh else T.STATUS_BUSY,
        )
        self.configure(
            border_color=T.GLASS_BORDER if self._fresh else T.STATUS_BUSY_BG,
        )


def _format_relative(timestamp: float) -> str:
    if timestamp <= 0:
        return "—"
    delta = time.time() - timestamp
    if delta < 1:
        return "just now"
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta / 60)}m ago"
    if delta < 86400:
        return f"{int(delta / 3600)}h ago"
    return f"{int(delta / 86400)}d ago"
