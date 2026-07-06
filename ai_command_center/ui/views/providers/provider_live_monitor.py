"""ProviderLiveMonitor — health card grid for the providers overview tab.

Architecture contract: pure display widget, data supplied via update().
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_STATUS_COLORS: dict[str, str] = {
    "healthy":  T.STATUS_READY,
    "ok":       T.STATUS_READY,
    "degraded": T.STATUS_BUSY,
    "error":    T.STATUS_ERROR,
    "offline":  T.TEXT_MUTED,
    "unknown":  T.TEXT_MUTED,
}


class _HealthCard(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        provider_id: str,
        name: str,
        health: str,
        latency_ms: float,
        tokens_used: int,
        error_count: int,
    ) -> None:
        color = _STATUS_COLORS.get(health.lower(), T.TEXT_MUTED)
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.CORNER_RADIUS,
            border_width=1,
            border_color=color,
        )

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            header,
            text="●",
            font=(T.FONT_FAMILY, 10),
            text_color=color,
            width=14,
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text=name or provider_id,
            font=(T.FONT_FAMILY, 12, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=(4, 0), fill="x", expand=True)
        ctk.CTkLabel(
            header,
            text=health.upper(),
            font=(T.FONT_FAMILY, 9),
            text_color=color,
        ).pack(side="right")

        metrics = ctk.CTkFrame(self, fg_color="transparent")
        metrics.pack(fill="x", padx=10, pady=(0, 8))
        metrics.columnconfigure(0, weight=1)
        metrics.columnconfigure(1, weight=1)
        metrics.columnconfigure(2, weight=1)

        for col, (label, value) in enumerate([
            ("Latency", f"{latency_ms:.0f}ms" if latency_ms else "—"),
            ("Tokens", f"{tokens_used:,}" if tokens_used else "—"),
            ("Errors", str(error_count) if error_count else "0"),
        ]):
            ctk.CTkLabel(
                metrics,
                text=label,
                font=(T.FONT_FAMILY, 8),
                text_color=T.TEXT_MUTED,
            ).grid(row=0, column=col, padx=2)
            ctk.CTkLabel(
                metrics,
                text=value,
                font=(T.FONT_FAMILY, 11, "bold"),
                text_color=T.STATUS_ERROR if label == "Errors" and error_count else T.TEXT_PRIMARY,
            ).grid(row=1, column=col, padx=2)


class ProviderLiveMonitor(ctk.CTkFrame):
    """Grid of health cards for all active providers."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)
        self._scroll.columnconfigure(0, weight=1)
        self._scroll.columnconfigure(1, weight=1)

    def update(self, providers: list[Any]) -> None:
        """Refresh the health card grid."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not providers:
            ctk.CTkLabel(
                self._scroll,
                text="No providers connected.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).grid(row=0, column=0, columnspan=2, pady=40)
            return

        for i, ph in enumerate(providers):
            if not isinstance(ph, (dict, object)):
                continue
            pid = str(getattr(ph, "provider_id", "") or (ph.get("provider_id", "") if isinstance(ph, dict) else ""))
            name = str(getattr(ph, "name", "") or (ph.get("name", pid) if isinstance(ph, dict) else pid))
            health = str(getattr(ph, "state", "") or (ph.get("state", ph.get("health_state", "unknown")) if isinstance(ph, dict) else "unknown"))
            latency = float(getattr(ph, "latency_ms", 0) or (ph.get("latency_ms", 0) if isinstance(ph, dict) else 0))
            tokens = int(getattr(ph, "tokens_used", 0) or (ph.get("tokens_used", 0) if isinstance(ph, dict) else 0))
            errors = int(getattr(ph, "error_count", 0) or (ph.get("error_count", 0) if isinstance(ph, dict) else 0))

            _HealthCard(
                self._scroll,
                provider_id=pid,
                name=name,
                health=health,
                latency_ms=latency,
                tokens_used=tokens,
                error_count=errors,
            ).grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="ew")
