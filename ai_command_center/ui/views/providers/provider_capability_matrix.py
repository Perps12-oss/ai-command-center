"""ProviderCapabilityMatrix — capability × provider matrix table.

Architecture contract: pure display widget, data supplied via update().
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class ProviderCapabilityMatrix(ctk.CTkFrame):
    """Capability × provider grid showing which provider handles which capability."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)

    def update(self, capability_providers: list[Any]) -> None:
        """Rebuild matrix from capability provider records."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not capability_providers:
            ctk.CTkLabel(
                self._scroll,
                text="No capability providers registered.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(pady=40)
            return

        # Collect all unique capabilities
        all_caps: set[str] = set()
        provider_caps: dict[str, set[str]] = {}
        for cp in capability_providers:
            pid = str(getattr(cp, "provider_id", "") or (cp.get("provider_id", "") if isinstance(cp, dict) else ""))
            caps = list(getattr(cp, "capabilities", ()) or (cp.get("capabilities", []) if isinstance(cp, dict) else []))
            provider_caps[pid] = set(str(c) for c in caps)
            all_caps.update(provider_caps[pid])

        if not all_caps:
            ctk.CTkLabel(
                self._scroll,
                text="No capabilities declared.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=20)
            return

        provider_ids = sorted(provider_caps.keys())
        caps_sorted = sorted(all_caps)

        # Header row
        header = ctk.CTkFrame(self._scroll, fg_color=T.BG_GLASS, corner_radius=0)
        header.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(
            header,
            text="Capability",
            font=(T.FONT_FAMILY, 10, "bold"),
            text_color=T.TEXT_SECONDARY,
            width=120,
            anchor="w",
        ).pack(side="left", padx=8, pady=4)

        for pid in provider_ids:
            ctk.CTkLabel(
                header,
                text=pid[:12],
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_MUTED,
                width=70,
                anchor="center",
            ).pack(side="left")

        # Capability rows
        for cap in caps_sorted:
            row = ctk.CTkFrame(
                self._scroll,
                fg_color=T.BG_PANEL,
                corner_radius=4,
                height=28,
            )
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            ctk.CTkLabel(
                row,
                text=cap[:22],
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_PRIMARY,
                width=120,
                anchor="w",
            ).pack(side="left", padx=8, pady=4)

            for pid in provider_ids:
                has = cap in provider_caps.get(pid, set())
                ctk.CTkLabel(
                    row,
                    text="✓" if has else "–",
                    font=(T.FONT_FAMILY, 11),
                    text_color=T.STATUS_READY if has else T.TEXT_MUTED,
                    width=70,
                    anchor="center",
                ).pack(side="left")
