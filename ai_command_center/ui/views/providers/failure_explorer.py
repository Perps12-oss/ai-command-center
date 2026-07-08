"""FailureExplorer — failure log explorer for the providers console.

Lists providers with error states and their recent failure messages.

Architecture contract: pure display widget, data supplied via update().
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class _FailureRow(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        provider_name: str,
        error_detail: str,
        error_count: int,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.STATUS_ERROR_BG,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=T.STATUS_ERROR,
        )
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)

        ctk.CTkLabel(
            row,
            text="✕",
            font=(T.FONT_FAMILY, 10),
            text_color=T.STATUS_ERROR,
            width=16,
        ).pack(side="left")

        ctk.CTkLabel(
            row,
            text=provider_name,
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=(4, 0), fill="x", expand=True)

        if error_count:
            ctk.CTkLabel(
                row,
                text=f"{error_count} errors",
                font=(T.FONT_FAMILY, 9),
                text_color=T.STATUS_ERROR,
            ).pack(side="right")

        if error_detail:
            ctk.CTkLabel(
                self,
                text=error_detail[:120],
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=380,
            ).pack(fill="x", padx=8, pady=(0, 6))


class FailureExplorer(ctk.CTkFrame):
    """List of providers in error/degraded states with failure details."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)

    def update(self, providers: list[Any]) -> None:
        """Show only providers in error/degraded state."""
        for child in self._scroll.winfo_children():
            child.destroy()

        failures = [
            ph for ph in providers
            if (
                str(getattr(ph, "state", "") or (ph.get("state", ph.get("health_state", "")) if isinstance(ph, dict) else ""))
                .lower() in {"error", "degraded", "offline"}
            )
        ]

        if not failures:
            ctk.CTkLabel(
                self._scroll,
                text="No failures — all providers healthy.",
                font=T.FONT_BODY,
                text_color=T.STATUS_READY,
            ).pack(pady=40)
            return

        for ph in failures:
            name = str(getattr(ph, "name", "") or (ph.get("name", ph.get("provider_id", "unknown")) if isinstance(ph, dict) else "unknown"))
            detail = str(getattr(ph, "detail", "") or (ph.get("detail", ph.get("health_detail", "")) if isinstance(ph, dict) else ""))
            errors = int(getattr(ph, "error_count", 0) or (ph.get("error_count", 0) if isinstance(ph, dict) else 0))

            _FailureRow(
                self._scroll,
                provider_name=name,
                error_detail=detail,
                error_count=errors,
            ).pack(fill="x", pady=4)
