"""Persist workflow run metadata and replay recent runs via EventBus."""

from __future__ import annotations

from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNS_LOADED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
)
from ai_command_center.repositories.workflow_run_repository import WorkflowRunRepository
from ai_command_center.services.base import BaseService


class WorkflowPersistenceService(BaseService):
    """Subscribes to workflow lifecycle events; persists metadata for replay."""

    name = "workflow_persistence"

    def __init__(self, bus, *, repo: WorkflowRunRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._unsubscribers: list[Callable[[], None]] = []
        self._step_index: dict[str, int] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(WORKFLOW_STARTED, self._on_workflow_started)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKFLOW_STEP_COMPLETED, self._on_step_completed)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKFLOW_COMPLETED, self._on_workflow_completed)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKFLOW_FAILED, self._on_workflow_failed)
        )
        self._publish_recent_runs()

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._step_index.clear()

    def _publish_recent_runs(self) -> None:
        runs = self._repo.list_recent()
        if not runs:
            return
        self._bus.publish(
            WORKFLOW_RUNS_LOADED,
            {
                "runs": [
                    {
                        "run_id": run.run_id,
                        "workflow_id": run.workflow_id,
                        "state": run.state,
                        "total_steps": run.total_steps,
                        "current_step_index": run.current_step_index,
                        "error": run.error,
                    }
                    for run in runs
                ]
            },
            source=self.name,
        )

    def _on_workflow_started(self, event: Event) -> None:
        payload = event.payload
        run_id = str(payload.get("run_id", "")).strip()
        if not run_id:
            return
        workflow_id = str(payload.get("workflow_id", ""))
        total_steps = int(payload.get("total_steps") or 0)
        steps = list(payload.get("steps") or [])
        self._step_index[run_id] = 0
        self._repo.upsert_started(
            run_id=run_id,
            workflow_id=workflow_id,
            total_steps=total_steps,
            steps=steps,
        )

    def _on_step_completed(self, event: Event) -> None:
        payload = event.payload
        run_id = str(payload.get("run_id", "")).strip()
        if not run_id:
            return
        index = int(payload.get("index", 0)) + 1
        self._step_index[run_id] = index
        self._repo.update_progress(run_id=run_id, current_step_index=index)

    def _on_workflow_completed(self, event: Event) -> None:
        payload = event.payload
        run_id = str(payload.get("run_id", "")).strip()
        if not run_id:
            return
        index = self._step_index.pop(run_id, int(payload.get("steps") or 0))
        self._repo.finalize(run_id=run_id, state="completed", current_step_index=index)

    def _on_workflow_failed(self, event: Event) -> None:
        payload = event.payload
        run_id = str(payload.get("run_id", "")).strip()
        if not run_id:
            return
        index = self._step_index.pop(run_id, 0)
        self._repo.finalize(
            run_id=run_id,
            state="failed",
            current_step_index=index,
            error=str(payload.get("error") or "workflow failed"),
        )
