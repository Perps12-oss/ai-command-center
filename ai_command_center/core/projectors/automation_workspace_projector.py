"""Automation workspace projection helpers."""

from __future__ import annotations

from typing import Any, Sequence

from ai_command_center.domain.automation_workspace import (
    AutomationCatalogItem,
    AutomationRunItem,
    AutomationScheduleItem,
    AutomationTemplateItem,
    AutomationWorkspaceState,
    WorkflowRunProjection,
)

_STATIC_CATALOG: tuple[AutomationCatalogItem, ...] = (
    AutomationCatalogItem(
        automation_id="auto-daily-sync",
        title="Daily Sync",
        description="Sync workspace entities and refresh indexes.",
        category="Operations",
        workflow_id="daily-sync",
        enabled=True,
    ),
    AutomationCatalogItem(
        automation_id="auto-report",
        title="Weekly Report",
        description="Generate artifact summary and notify providers.",
        category="Reporting",
        workflow_id="weekly-report",
        enabled=True,
    ),
    AutomationCatalogItem(
        automation_id="auto-demo",
        title="Demo Linear Flow",
        description="Three-step shell workflow used by the graph workspace.",
        category="Demo",
        workflow_id="demo-linear",
        enabled=True,
    ),
)

_STATIC_SCHEDULES: tuple[AutomationScheduleItem, ...] = (
    AutomationScheduleItem(
        schedule_id="sched-daily",
        workflow_id="daily-sync",
        cron="0 6 * * *",
        title="Daily Sync",
        enabled=True,
        next_run_label="06:00 daily",
    ),
    AutomationScheduleItem(
        schedule_id="sched-weekly",
        workflow_id="weekly-report",
        cron="0 8 * * 1",
        title="Weekly Report",
        enabled=False,
        next_run_label="Mon 08:00",
    ),
)

_STATIC_TEMPLATES: tuple[AutomationTemplateItem, ...] = (
    AutomationTemplateItem(
        template_id="tpl-onboard",
        title="Onboarding Flow",
        description="Plan, execute, and publish onboarding artifacts.",
        category="Getting Started",
        step_count=3,
        workflow_id="demo-linear",
    ),
    AutomationTemplateItem(
        template_id="tpl-incident",
        title="Incident Triage",
        description="Collect traces, inspect providers, and file a decision.",
        category="Reliability",
        step_count=4,
        workflow_id="weekly-report",
    ),
    AutomationTemplateItem(
        template_id="tpl-research",
        title="Research Loop",
        description="Search notes, summarize memory, and draft a report.",
        category="Knowledge",
        step_count=5,
        workflow_id="daily-sync",
    ),
)

_DEMO_STEPS: tuple[dict[str, Any], ...] = (
    {"id": "plan", "name": "Plan", "type": "tool", "tool": "shell", "args": {"command": "echo plan"}},
    {"id": "execute", "name": "Execute", "type": "tool", "tool": "shell", "args": {"command": "echo execute"}},
    {"id": "report", "name": "Report", "type": "tool", "tool": "shell", "args": {"command": "echo report"}},
)

_WORKFLOW_STEPS: dict[str, list[dict[str, Any]]] = {
    "demo-linear": [dict(step) for step in _DEMO_STEPS],
    "daily-sync": [
        {"id": "index", "name": "Index Notes", "type": "tool", "tool": "shell", "args": {"command": "echo index"}},
        {"id": "sync", "name": "Sync Workspace", "type": "tool", "tool": "shell", "args": {"command": "echo sync"}},
    ],
    "weekly-report": [
        {"id": "collect", "name": "Collect Metrics", "type": "tool", "tool": "shell", "args": {"command": "echo collect"}},
        {"id": "summarize", "name": "Summarize", "type": "tool", "tool": "shell", "args": {"command": "echo summarize"}},
        {"id": "publish", "name": "Publish Report", "type": "tool", "tool": "shell", "args": {"command": "echo publish"}},
    ],
}


class AutomationWorkspaceProjector:
    """Project workflow runs into automation workspace slices."""

    @staticmethod
    def catalog() -> tuple[AutomationCatalogItem, ...]:
        return _STATIC_CATALOG

    @staticmethod
    def schedules() -> tuple[AutomationScheduleItem, ...]:
        return _STATIC_SCHEDULES

    @staticmethod
    def templates() -> tuple[AutomationTemplateItem, ...]:
        return _STATIC_TEMPLATES

    @staticmethod
    def steps_for_workflow(workflow_id: str) -> list[dict[str, Any]]:
        return [dict(step) for step in _WORKFLOW_STEPS.get(workflow_id, _WORKFLOW_STEPS["demo-linear"])]

    @staticmethod
    def run_item(run: WorkflowRunProjection) -> AutomationRunItem:
        total = max(run.total_steps, 1)
        index = max(0, min(run.current_step_index, total))
        if run.state == "completed":
            progress = 1.0
        elif run.state == "failed":
            progress = index / total
        elif run.state == "running":
            progress = index / total if total else 0.0
        else:
            progress = 0.0
        title = run.workflow_id.replace("-", " ").title() or run.run_id[:12]
        return AutomationRunItem(
            run_id=run.run_id,
            workflow_id=run.workflow_id,
            title=title,
            state=run.state,
            progress=progress,
            current_step_index=run.current_step_index,
            total_steps=run.total_steps,
            error=run.error,
        )

    @staticmethod
    def project_runs(
        workflow_runs: Sequence[WorkflowRunProjection],
    ) -> tuple[tuple[AutomationRunItem, ...], tuple[AutomationRunItem, ...]]:
        active: list[AutomationRunItem] = []
        failures: list[AutomationRunItem] = []
        for run in workflow_runs:
            item = AutomationWorkspaceProjector.run_item(run)
            if run.state == "running":
                active.append(item)
            elif run.state == "failed":
                failures.append(item)
        return tuple(active), tuple(failures)

    @staticmethod
    def project_state(
        workflow_runs: Sequence[WorkflowRunProjection],
        *,
        selected_failure_run_id: str = "",
        revision: int = 0,
        schedules: Sequence[AutomationScheduleItem] | None = None,
    ) -> AutomationWorkspaceState:
        active, failures = AutomationWorkspaceProjector.project_runs(workflow_runs)
        sched = (
            tuple(schedules)
            if schedules is not None
            else AutomationWorkspaceProjector.schedules()
        )
        return AutomationWorkspaceState(
            catalog=AutomationWorkspaceProjector.catalog(),
            active_runs=active,
            schedules=sched,
            failures=failures,
            templates=AutomationWorkspaceProjector.templates(),
            selected_failure_run_id=selected_failure_run_id,
            revision=revision,
        )


__all__ = ["AutomationWorkspaceProjector"]
