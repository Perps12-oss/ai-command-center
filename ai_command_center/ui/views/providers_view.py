"""ProvidersView — provider health dashboard.

Sections:
  Dashboard cards (health / latency / tokens / errors / cost)
  Live monitor grid
  Capability matrix
  Failure explorer

Architecture contract: pure display view, no bus/service imports.
Data supplied via apply_state() from the UIQueue/StateApplierMixin.
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.providers.provider_live_monitor import ProviderLiveMonitor
from ai_command_center.ui.views.providers.provider_capability_matrix import ProviderCapabilityMatrix
from ai_command_center.ui.views.providers.failure_explorer import FailureExplorer

_TABS: tuple[str, ...] = ("Overview", "Capabilities", "Failures")


class ProvidersView(ctk.CTkFrame):
    """Provider console main view — tabbed layout.

    ┌────────────────────────────────────────┐
    │ Providers                              │
    │ [Overview] [Capabilities] [Failures]  │
    │ ─────────────────────────────────────  │
    │ <tab content>                          │
    └────────────────────────────────────────┘
    """

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._active_tab = "Overview"
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        self._tab_frames: dict[str, ctk.CTkFrame] = {}
        self._build()

    def _build(self) -> None:
        # Page header
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Providers",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=T.PAD, pady=12)

        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=34)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        for tab in _TABS:
            btn = ctk.CTkButton(
                tab_bar,
                text=tab,
                height=30,
                font=(T.FONT_FAMILY, 11),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=T.TEXT_MUTED,
                corner_radius=0,
                command=lambda t=tab: self._show_tab(t),
            )
            btn.pack(side="left", padx=2)
            self._tab_buttons[tab] = btn

        ctk.CTkFrame(self, height=1, fg_color=T.BG_GLASS_BORDER).pack(fill="x")

        # Content
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        self._tab_frames["Overview"] = ProviderLiveMonitor(self._content)
        self._tab_frames["Capabilities"] = ProviderCapabilityMatrix(self._content)
        self._tab_frames["Failures"] = FailureExplorer(self._content)

        self._show_tab("Overview")

    def _show_tab(self, name: str) -> None:
        self._active_tab = name
        for t, frame in self._tab_frames.items():
            frame.pack_forget()
        self._tab_frames[name].pack(fill="both", expand=True)
        for t, btn in self._tab_buttons.items():
            btn.configure(
                text_color=T.TEXT_PRIMARY if t == name else T.TEXT_MUTED,
                fg_color=T.BG_GLASS if t == name else "transparent",
            )

    def apply_state(self, provider_health_map: Any, capability_providers: Any) -> None:
        """Refresh all tabs from AppState projections."""
        providers = list(provider_health_map or [])
        caps = list(capability_providers or [])

        self._tab_frames["Overview"].update(providers)  # type: ignore[union-attr]
        self._tab_frames["Capabilities"].update(caps)  # type: ignore[union-attr]
        self._tab_frames["Failures"].update(providers)  # type: ignore[union-attr]
