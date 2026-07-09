"""AutomationWorkspaceView — ops console for automations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.automation_workspace import AutomationWorkspaceState
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.automation.active_runs_panel import ActiveRunsPanel
from ai_command_center.ui.views.automation.automation_catalog import AutomationCatalog
from ai_command_center.ui.views.automation.failure_queue import FailureQueue
from ai_command_center.ui.views.automation.schedule_manager import ScheduleManager
from ai_command_center.ui.views.automation.template_gallery import TemplateGallery


class AutomationWorkspaceView(ctk.CTkFrame):
    """Automation workspace composing catalog, runs, schedules, templates, failures."""

    def __init__(
        self,
        master: Any,
        *,
        on_run: Callable[[str], None] | None = None,
        on_select_failure: Callable[[str], None] | None = None,
        on_scrub: Callable[[int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_run = on_run or (lambda _workflow_id: None)
        self._on_select_failure = on_select_failure or (lambda _run_id: None)
        self._on_scrub = on_scrub or (lambda _index: None)
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Automation Workspace",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=T.PAD, pady=12)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="both", expand=True)

        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=1)
        top.grid_rowconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)

        self._catalog = AutomationCatalog(top, on_run=self._on_run)
        self._catalog.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))

        self._active_runs = ActiveRunsPanel(top)
        self._active_runs.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))

        self._schedules = ScheduleManager(top)
        self._schedules.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))

        self._templates = TemplateGallery(top)
        self._templates.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

        self._failures = FailureQueue(
            self,
            on_select=self._on_select_failure,
            on_scrub=self._on_scrub,
        )
        self._failures.pack(fill="x", side="bottom")

    def apply_state(self, state: AutomationWorkspaceState) -> None:
        self._catalog.update(state.catalog)
        self._active_runs.update(state.active_runs)
        self._schedules.update(state.schedules)
        self._templates.update(state.templates)
        self._failures.update(
            state.failures,
            selected_run_id=state.selected_failure_run_id,
        )

    def show_inspector(self, ref: InspectableRef) -> None:
        self._failures.show_inspector(ref)

    def clear_inspector(self) -> None:
        self._failures.clear_inspector()


__all__ = ["AutomationWorkspaceView"]
