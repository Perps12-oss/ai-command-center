"""InspectorPanel — Langflow-inspired docked right-rail execution inspector.

Tabs (left to right):
  Trace      — execution span tree
  Provider   — provider health cards
  Artifacts  — artifact list
  Metrics    — KPI metric cards

Data flows in via update() called from the StateApplierMixin UIQueue path.
Actions publish via on_artifact_action (→ UIController → EventBus).

Architecture contract
─────────────────────
• Pure display panel — no EventBus, service, or repository imports.
• Data supplied via public update() method.
• Reference: Langflow docked inspector; runtime_inspector.py patterns.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.inspector.inspector_artifacts_tab import (
    InspectorArtifactsTab,
)
from ai_command_center.ui.views.chat.inspector.inspector_metrics_tab import (
    InspectorMetricsTab,
)
from ai_command_center.ui.views.chat.inspector.inspector_provider_tab import (
    InspectorProviderTab,
)
from ai_command_center.ui.views.chat.inspector.inspector_trace_tab import (
    InspectorTraceTab,
)

_TABS: tuple[str, ...] = ("Trace", "Provider", "Artifacts", "Metrics")


class InspectorPanel(ctk.CTkFrame):
    """Docked right-rail inspector panel for the chat workspace.

    ┌─────────────────────────┐
    │  [Trace][Provider][...]  │
    │ ─────────────────────── │
    │  <tab content>           │
    └─────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        *,
        on_artifact_action: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            corner_radius=0,
            **kwargs,
        )
        self._on_artifact_action = on_artifact_action
        self._active_tab: str = "Trace"
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        self._tab_frames: dict[str, ctk.CTkFrame] = {}

        self._build()

    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color=T.BG_GLASS, corner_radius=0, height=36)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Inspector",
            font=(T.FONT_FAMILY, 11, "bold"),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        ).pack(side="left", padx=10, pady=8)

        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color=T.BG_GLASS_BORDER, corner_radius=0, height=30)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        for tab_name in _TABS:
            btn = ctk.CTkButton(
                tab_bar,
                text=tab_name,
                width=60, height=26,
                font=(T.FONT_FAMILY, 10),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=T.TEXT_MUTED,
                corner_radius=0,
                command=lambda t=tab_name: self._show_tab(t),
            )
            btn.pack(side="left")
            self._tab_buttons[tab_name] = btn

        # Content area
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        # Build tab frames
        self._tab_frames["Trace"] = InspectorTraceTab(self._content)
        self._tab_frames["Provider"] = InspectorProviderTab(self._content)
        self._tab_frames["Artifacts"] = InspectorArtifactsTab(
            self._content,
            on_artifact_action=self._on_artifact_action,
        )
        self._tab_frames["Metrics"] = InspectorMetricsTab(self._content)

        self._show_tab("Trace")

    def _show_tab(self, name: str) -> None:
        self._active_tab = name
        for tab_name, frame in self._tab_frames.items():
            frame.pack_forget()
        self._tab_frames[name].pack(fill="both", expand=True)

        for tab_name, btn in self._tab_buttons.items():
            btn.configure(
                text_color=T.TEXT_PRIMARY if tab_name == name else T.TEXT_MUTED,
                fg_color=T.BG_GLASS if tab_name == name else "transparent",
            )

    def update(self, context: "Any") -> None:
        """Apply an ExecutionContext snapshot to all tabs.

        ``context`` is an ExecutionContext dataclass (or any duck-type with
        the same fields).
        """
        spans = [
            {
                "span_id": s.span_id,
                "parent_id": s.parent_id,
                "name": s.name,
                "kind": s.kind,
                "status": s.status,
                "duration_ms": s.duration_ms,
            }
            for s in getattr(context, "trace_spans", ())
        ]
        self._tab_frames["Trace"].update(spans)  # type: ignore[union-attr]

        provider_health = [
            {
                "provider_id": getattr(context, "provider_id", ""),
                "name": getattr(context, "provider_id", ""),
                "health_state": "healthy",
                "model": getattr(context, "model", ""),
                "latency_ms": 0,
            }
        ]
        self._tab_frames["Provider"].update(  # type: ignore[union-attr]
            provider_id=getattr(context, "provider_id", ""),
            provider_health_map=provider_health,
        )

        artifacts = [
            {
                "artifact_id": a.artifact_id,
                "kind": a.kind,
                "label": a.label,
                "size_bytes": a.size_bytes,
            }
            for a in getattr(context, "artifacts", ())
        ]
        self._tab_frames["Artifacts"].update(artifacts)  # type: ignore[union-attr]

        self._tab_frames["Metrics"].update(getattr(context, "metrics", {}))  # type: ignore[union-attr]
