"""Execution inspector using collapsible sections."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.core.state.execution_state import ExecutionContext
from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector.base_inspector import BaseInspector
from ai_command_center.ui.components.inspector.collapsible_section import CollapsibleSection
from ai_command_center.ui.components.execution_timeline_list import ExecutionTimelineList
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


class ExecutionInspector(BaseInspector):
    """Renders the current execution context as expandable sections.

    Data arrives via update_context() from the chat view's public projection
    path; BaseInspector.update() is a no-op because selection refs are handled
    separately by InspectorHost.
    """

    def __init__(
        self,
        master: Any,
        *,
        on_artifact_action: Callable[[str, str], None] | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_inspect_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._last_context: ExecutionContext | None = None
        self._timeline_events: tuple[ExecutionEvent, ...] = ()
        self._timeline_request_id: str = ""

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True)

        self.trace_section = CollapsibleSection(self._scroll, title="Trace")
        self.trace_section.pack(fill="x", padx=0, pady=(0, 8))
        self._trace_tab = InspectorTraceTab(self.trace_section.body)
        self._trace_tab.pack(fill="both", expand=True)

        self.timeline_section = CollapsibleSection(self._scroll, title="Timeline")
        self.timeline_section.pack(fill="x", padx=0, pady=(0, 8))
        self._timeline_list = ExecutionTimelineList(
            self.timeline_section.body,
            on_select=on_inspect_select,
            on_navigate=on_inspect_navigate,
        )
        self._timeline_list.pack(fill="both", expand=True)

        self.provider_section = CollapsibleSection(self._scroll, title="Provider")
        self.provider_section.pack(fill="x", padx=0, pady=(0, 8))
        self._provider_tab = InspectorProviderTab(self.provider_section.body)
        self._provider_tab.pack(fill="both", expand=True)

        self.artifacts_section = CollapsibleSection(self._scroll, title="Artifacts")
        self.artifacts_section.pack(fill="x", padx=0, pady=(0, 8))
        self._artifacts_tab = InspectorArtifactsTab(
            self.artifacts_section.body,
            on_artifact_action=on_artifact_action,
        )
        self._artifacts_tab.pack(fill="both", expand=True)

        self.metrics_section = CollapsibleSection(self._scroll, title="Metrics")
        self.metrics_section.pack(fill="x", padx=0, pady=(0, 8))
        self._metrics_tab = InspectorMetricsTab(self.metrics_section.body)
        self._metrics_tab.pack(fill="both", expand=True)

    def update_context(self, context: ExecutionContext | Any) -> None:
        """Project the active ExecutionContext into the four section widgets."""
        self._last_context = context
        self._timeline_request_id = str(getattr(context, "request_id", "") or "").strip()

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
        self._trace_tab.update(spans)
        self.trace_section.set_title(f"Trace ({len(spans)})" if spans else "Trace")

        provider_health = [
            {
                "provider_id": getattr(context, "provider_id", ""),
                "name": getattr(context, "provider_id", ""),
                "health_state": "healthy",
                "model": getattr(context, "model", ""),
                "latency_ms": 0,
            }
        ]
        self._provider_tab.update(
            provider_id=getattr(context, "provider_id", ""),
            provider_health_map=provider_health,
        )
        provider_title = (
            f"Provider ({len(provider_health)})" if provider_health else "Provider"
        )
        self.provider_section.set_title(provider_title)

        artifacts = [
            {
                "artifact_id": a.artifact_id,
                "kind": a.kind,
                "label": a.label,
                "size_bytes": a.size_bytes,
            }
            for a in getattr(context, "artifacts", ())
        ]
        self._artifacts_tab.update(artifacts)
        self.artifacts_section.set_title(
            f"Artifacts ({len(artifacts)})" if artifacts else "Artifacts"
        )

        metrics = dict(getattr(context, "metrics", {}) or {})
        self._metrics_tab.update(metrics)
        self.metrics_section.set_title(
            f"Metrics ({len(metrics)})" if metrics else "Metrics"
        )
        self._refresh_timeline()

    def update_timeline(self, events: Sequence[ExecutionEvent]) -> None:
        """Refresh the execution timeline section from the AppState projection."""
        self._timeline_events = tuple(events)
        self._refresh_timeline()

    def _refresh_timeline(self) -> None:
        request_id = self._timeline_request_id
        if request_id:
            filtered = tuple(
                event for event in self._timeline_events if event.request_id == request_id
            )
        else:
            filtered = self._timeline_events
        self._timeline_list.set_events(filtered)
        title = f"Timeline ({len(filtered)})" if filtered else "Timeline"
        self.timeline_section.set_title(title)

    def update(self, ref: InspectableRef) -> None:
        """BaseInspector contract; execution content is projected via update_context()."""
        return None


__all__ = ["ExecutionInspector"]
