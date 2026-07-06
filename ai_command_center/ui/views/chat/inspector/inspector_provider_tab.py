"""InspectorProviderTab — provider health for the inspector panel.

Reference: Langflow provider panel, reuses patterns from runtime_inspector.py.

Architecture contract: pure display widget, data supplied via update().
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_STATUS_COLORS: dict[str, str] = {
    "healthy":   T.STATUS_READY,
    "ok":        T.STATUS_READY,
    "degraded":  T.STATUS_BUSY,
    "error":     T.STATUS_ERROR,
    "offline":   T.TEXT_MUTED,
    "unknown":   T.TEXT_MUTED,
}


class _ProviderCard(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        provider_id: str,
        name: str,
        health: str,
        latency_ms: float,
        model: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
            **kwargs,
        )
        color = _STATUS_COLORS.get(health.lower(), T.TEXT_MUTED)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            header,
            text="●",
            font=(T.FONT_FAMILY, 9),
            text_color=color,
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text=name or provider_id,
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=(4, 0), fill="x", expand=True)
        ctk.CTkLabel(
            header,
            text=health.upper(),
            font=(T.FONT_FAMILY, 9),
            text_color=color,
        ).pack(side="right")

        sub = ctk.CTkFrame(self, fg_color="transparent")
        sub.pack(fill="x", padx=8, pady=(0, 6))
        if model:
            ctk.CTkLabel(
                sub,
                text=model,
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(side="left")
        if latency_ms > 0:
            ctk.CTkLabel(
                sub,
                text=f"{latency_ms:.0f}ms",
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_MUTED,
            ).pack(side="right")


class InspectorProviderTab(ctk.CTkFrame):
    """Shows active provider health and latency cards."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)

    def update(
        self,
        provider_id: str,
        provider_health_map: list[dict],
    ) -> None:
        """Refresh the provider cards."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not provider_health_map:
            ctk.CTkLabel(
                self._scroll,
                text="No provider data",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=20)
            return

        for ph in provider_health_map:
            if not isinstance(ph, dict):
                continue
            _ProviderCard(
                self._scroll,
                provider_id=str(ph.get("provider_id", "")),
                name=str(ph.get("name", ph.get("provider_id", "unknown"))),
                health=str(ph.get("state", ph.get("health_state", "unknown"))),
                latency_ms=float(ph.get("latency_ms", 0)),
                model=str(ph.get("model", "")),
            ).pack(fill="x", padx=4, pady=3)
