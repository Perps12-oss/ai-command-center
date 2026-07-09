"""Failed automation runs queue with bottom docks."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.automation_workspace import AutomationRunItem
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.docks.execution_timeline_dock import ExecutionTimelineDock
from ai_command_center.ui.components.docks.inspector_dock import InspectorDock
from ai_command_center.ui.components.inspector.workflow_node_inspector import WorkflowNodeInspector
from ai_command_center.ui.design_system import theme_v2 as T


class FailureQueue(ctk.CTkFrame):
    """Failure list with execution timeline and inspector docks."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
        on_scrub: Callable[[int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0, **kwargs)
        self._on_select = on_select or (lambda _run_id: None)
        self._on_scrub = on_scrub or (lambda _index: None)
        self._selected_run_id = ""

        ctk.CTkLabel(
            self,
            text="FAILURE QUEUE",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._list = ctk.CTkScrollableFrame(self, fg_color="transparent", height=88, corner_radius=0)
        self._list.pack(fill="x", padx=T.PAD)

        dock_row = ctk.CTkFrame(self, fg_color="transparent")
        dock_row.pack(fill="both", expand=True, pady=(4, 0))

        split = tk.PanedWindow(
            dock_row,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief=tk.FLAT,
            background=T.BG_GLASS_BORDER,
            handlesize=0,
            showhandle=False,
        )
        split.pack(fill="both", expand=True)

        timeline_host = ctk.CTkFrame(split, fg_color=T.BG_DEEP, corner_radius=0)
        inspector_host = ctk.CTkFrame(split, fg_color=T.BG_PANEL, corner_radius=0)
        split.add(timeline_host, minsize=280, stretch="always")
        split.add(inspector_host, minsize=220, stretch="never")

        self._timeline_dock = ExecutionTimelineDock(
            timeline_host,
            on_scrub=self._on_scrub,
            timeline_height=64,
        )
        self._timeline_dock.pack(fill="both", expand=True)

        self._inspector_dock = InspectorDock(inspector_host)
        self._workflow_inspector = WorkflowNodeInspector(self._inspector_dock.host)
        self._inspector_dock.register("workflow", self._workflow_inspector)
        self._inspector_dock.set_default(self._workflow_inspector)
        self._inspector_dock.pack(fill="both", expand=True)

    def update(
        self,
        failures: Sequence[AutomationRunItem],
        *,
        selected_run_id: str = "",
    ) -> None:
        self._selected_run_id = selected_run_id
        for child in self._list.winfo_children():
            child.destroy()
        if not failures:
            ctk.CTkLabel(
                self._list,
                text="No failed runs",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(anchor="w", pady=6)
            self._timeline_dock.render([])
            return

        selected: AutomationRunItem | None = None
        for failure in failures:
            if failure.run_id == selected_run_id:
                selected = failure
            row = ctk.CTkFrame(self._list, fg_color=T.BG_GLASS, corner_radius=T.SMALL_RADIUS)
            row.pack(fill="x", pady=2)
            ctk.CTkButton(
                row,
                text=failure.title,
                anchor="w",
                font=(T.FONT_FAMILY, 10),
                fg_color=T.STATUS_ERROR_BG if failure.run_id == selected_run_id else T.BG_GLASS,
                hover_color=T.BG_GLASS_BORDER,
                text_color=T.TEXT_PRIMARY,
                command=lambda rid=failure.run_id: self._on_select(rid),
            ).pack(fill="x", padx=4, pady=4)
            if failure.error:
                ctk.CTkLabel(
                    row,
                    text=failure.error[:100],
                    font=(T.FONT_FAMILY, 9),
                    text_color=T.STATUS_ERROR,
                    anchor="w",
                ).pack(fill="x", padx=10, pady=(0, 6))

        if selected is None:
            selected = failures[0]
        steps = [
            {
                "name": f"Step {index + 1}",
                "status": "failed" if index >= selected.current_step_index else "completed",
                "duration_ms": 0.0,
            }
            for index in range(max(selected.total_steps, 1))
        ]
        labels = [step["name"] for step in steps]
        active_index = max(0, min(selected.current_step_index, len(steps) - 1))
        self._timeline_dock.render(steps, scrub_labels=labels, scrub_index=active_index)

    def show_inspector(self, ref: InspectableRef) -> None:
        self._inspector_dock.show(ref)

    def clear_inspector(self) -> None:
        self._inspector_dock.clear()


__all__ = ["FailureQueue"]
