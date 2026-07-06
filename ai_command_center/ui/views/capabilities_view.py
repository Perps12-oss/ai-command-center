"""CapabilitiesView — capability catalog from capability_lifecycle AppState.

Lists all registered capabilities with their lifecycle state,
provider assignment, and health status.

Architecture contract: pure display view, no bus/service imports.
Data supplied via apply_state() from the UIQueue.
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_STAGE_COLORS: dict[str, str] = {
    "active":      T.STATUS_READY,
    "activating":  T.STATUS_BUSY,
    "degraded":    T.STATUS_BUSY,
    "failed":      T.STATUS_ERROR,
    "inactive":    T.TEXT_MUTED,
    "unknown":     T.TEXT_MUTED,
}


class _CapabilityRow(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        name: str,
        kind: str,
        stage: str,
        provider: str,
        version: str,
    ) -> None:
        super().__init__(master, fg_color=T.BG_GLASS, corner_radius=T.SMALL_RADIUS, height=40)
        self.pack_propagate(False)
        color = _STAGE_COLORS.get(stage.lower(), T.TEXT_MUTED)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=8, pady=6)

        ctk.CTkLabel(
            row,
            text="●",
            font=(T.FONT_FAMILY, 8),
            text_color=color,
            width=12,
        ).pack(side="left")

        ctk.CTkLabel(
            row,
            text=name,
            font=(T.FONT_FAMILY, 11),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=(4, 0), fill="x", expand=True)

        if provider:
            ctk.CTkLabel(
                row,
                text=provider[:16],
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
            ).pack(side="right", padx=(0, 8))

        ctk.CTkLabel(
            row,
            text=stage.upper(),
            font=(T.FONT_FAMILY, 8),
            text_color=color,
            width=70,
        ).pack(side="right")


class CapabilitiesView(ctk.CTkFrame):
    """Capability catalog page."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Capabilities",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=T.PAD, pady=12)

        # Column headers
        col_header = ctk.CTkFrame(self, fg_color=T.BG_GLASS, corner_radius=0, height=28)
        col_header.pack(fill="x")
        col_header.pack_propagate(False)
        for label, pad in [("Name", 20), ("Stage", 0), ("Provider", 0)]:
            ctk.CTkLabel(
                col_header,
                text=label,
                font=(T.FONT_FAMILY, 9, "bold"),
                text_color=T.TEXT_MUTED,
            ).pack(side="left", padx=pad, pady=4)

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(
            self._scroll,
            text="No capabilities registered.",
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
        ).pack(pady=40)

    def apply_state(self, capability_lifecycle: Any) -> None:
        """Refresh from AppState.capability_lifecycle."""
        for child in self._scroll.winfo_children():
            child.destroy()

        records = list(capability_lifecycle or [])
        if not records:
            ctk.CTkLabel(
                self._scroll,
                text="No capabilities registered.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(pady=40)
            return

        for rec in records:
            name = str(getattr(rec, "capability_id", "") or getattr(rec, "name", ""))
            kind = str(getattr(rec, "kind", ""))
            stage = str(getattr(rec, "stage", getattr(rec, "state", "unknown")))
            provider = str(getattr(rec, "provider_id", ""))
            version = str(getattr(rec, "version", ""))

            _CapabilityRow(
                self._scroll,
                name=name,
                kind=kind,
                stage=stage,
                provider=provider,
                version=version,
            ).pack(fill="x", pady=2)
