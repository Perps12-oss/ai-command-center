"""Automation workspace domain projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class WorkflowRunProjection(Protocol):
    run_id: str
    workflow_id: str
    state: str
    current_step_id: str
    current_step_index: int
    total_steps: int
    error: str


@dataclass(frozen=True, slots=True)
class AutomationCatalogItem:
    automation_id: str = ""
    title: str = ""
    description: str = ""
    category: str = ""
    workflow_id: str = ""
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class AutomationRunItem:
    run_id: str = ""
    workflow_id: str = ""
    title: str = ""
    state: str = "pending"
    progress: float = 0.0
    current_step_index: int = 0
    total_steps: int = 0
    error: str = ""


@dataclass(frozen=True, slots=True)
class AutomationScheduleItem:
    schedule_id: str = ""
    workflow_id: str = ""
    cron: str = ""
    title: str = ""
    enabled: bool = True
    next_run_label: str = ""


@dataclass(frozen=True, slots=True)
class AutomationTemplateItem:
    template_id: str = ""
    title: str = ""
    description: str = ""
    category: str = ""
    step_count: int = 0


@dataclass(frozen=True, slots=True)
class AutomationWorkspaceState:
    catalog: tuple[AutomationCatalogItem, ...] = ()
    active_runs: tuple[AutomationRunItem, ...] = ()
    schedules: tuple[AutomationScheduleItem, ...] = ()
    failures: tuple[AutomationRunItem, ...] = ()
    templates: tuple[AutomationTemplateItem, ...] = ()
    selected_failure_run_id: str = ""
    revision: int = 0


__all__ = [
    "AutomationCatalogItem",
    "AutomationRunItem",
    "AutomationScheduleItem",
    "AutomationTemplateItem",
    "AutomationWorkspaceState",
    "WorkflowRunProjection",
]
