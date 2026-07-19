"""EventBus-driven workflow definition / status provider (W0/W1).

Does **not** publish TOOL_INVOKE. ExecutionAuthority converts WORKFLOW_START into
an ExecutionPlan; ExecutionOrchestrator alone dispatches tools. This service
publishes workflow lifecycle status by observing execution runs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ai_command_center.core.contracts import build_workspace_context
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_STARTED,
    EXECUTION_STEP_COMPLETED,
    EXECUTION_STEP_FAILED,
    EXECUTION_STEP_STARTED,
    TELEMETRY_EVENT,
    WORKFLOW_COMPLETED,
    WORKFLOW_EXECUTION_REQUEST,
    WORKFLOW_FAILED,
    WORKFLOW_START,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)


class WorkflowEngineService(BaseService):
    """Workflow definition + status projection. Never publishes TOOL_INVOKE."""

    name = "workflow_engine"
    _MAX_STEPS = 16

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._runs: dict[str, dict[str, Any]] = {}
        self._execution_to_workflow: dict[str, str] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(WORKFLOW_START, self._on_workflow_start)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_RUN_STARTED, self._on_execution_started)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_STEP_STARTED, self._on_execution_step_started)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_STEP_COMPLETED, self._on_execution_step_completed)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_STEP_FAILED, self._on_execution_step_failed)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_RUN_COMPLETE, self._on_execution_complete)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_RUN_FAILED, self._on_execution_failed)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._runs.clear()
        self._execution_to_workflow.clear()

    def _on_workflow_start(self, event: Event) -> None:
        import uuid

        run_id = str(event.payload.get("run_id") or uuid.uuid4().hex)
        steps = list(event.payload.get("steps") or [])
        if not steps:
            self._bus.publish(
                WORKFLOW_FAILED,
                {"run_id": run_id, "error": "workflow has no steps"},
                source=self.name,
            )
            return
        if len(steps) > self._MAX_STEPS:
            self._bus.publish(
                WORKFLOW_FAILED,
                {"run_id": run_id, "error": "max workflow steps exceeded"},
                source=self.name,
            )
            return
        workflow_id = str(event.payload.get("workflow_id") or "")
        workspace_context = event.payload.get("workspace_context")
        if not isinstance(workspace_context, dict):
            workspace_context = build_workspace_context(
                workspace_id=event.payload.get("workspace_id"),
                entity_id=event.payload.get("entity_id"),
                entity_type=event.payload.get("entity_type"),
            )
        self._runs[run_id] = {
            "steps": steps,
            "index": 0,
            "workflow_id": workflow_id,
            "workspace_context": workspace_context,
            "total_steps": len(steps),
        }
        _logger.info("workflow.start run_id=%s steps=%d", run_id, len(steps))
        started_payload = {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "total_steps": len(steps),
            "steps": steps,
        }
        self._bus.publish(WORKFLOW_STARTED, started_payload, source=self.name)
        # Hand off to ExecutionAuthority after local status registration.
        intake = dict(event.payload)
        intake["run_id"] = run_id
        if workspace_context and "workspace_context" not in intake:
            intake["workspace_context"] = workspace_context
        self._bus.publish(WORKFLOW_EXECUTION_REQUEST, intake, source=self.name)

    def _on_execution_started(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or "")
        execution_run_id = str(event.payload.get("run_id") or "")
        if request_id in self._runs and execution_run_id:
            self._execution_to_workflow[execution_run_id] = request_id

    def _workflow_id_for_execution(self, execution_run_id: str) -> str:
        return self._execution_to_workflow.get(execution_run_id, "")

    def _on_execution_step_started(self, event: Event) -> None:
        execution_run_id = str(event.payload.get("run_id") or "")
        workflow_run_id = self._workflow_id_for_execution(execution_run_id)
        if not workflow_run_id or workflow_run_id not in self._runs:
            return
        run = self._runs[workflow_run_id]
        index = int(event.payload.get("index", run.get("index", 0)))
        step_id = str(event.payload.get("step_id") or f"step-{index}")
        self._bus.publish(
            WORKFLOW_STEP_STARTED,
            {
                "run_id": workflow_run_id,
                "step_id": step_id,
                "index": index,
                "type": "tool",
            },
            source=self.name,
        )

    def _on_execution_step_completed(self, event: Event) -> None:
        execution_run_id = str(event.payload.get("run_id") or "")
        workflow_run_id = self._workflow_id_for_execution(execution_run_id)
        if not workflow_run_id or workflow_run_id not in self._runs:
            return
        run = self._runs[workflow_run_id]
        index = int(event.payload.get("index", run.get("index", 0)))
        step_id = str(event.payload.get("step_id") or f"step-{index}")
        self._bus.publish(
            WORKFLOW_STEP_COMPLETED,
            {
                "run_id": workflow_run_id,
                "step_id": step_id,
                "index": index,
                "success": True,
            },
            source=self.name,
        )
        run["index"] = index + 1

    def _on_execution_step_failed(self, event: Event) -> None:
        execution_run_id = str(event.payload.get("run_id") or "")
        workflow_run_id = self._workflow_id_for_execution(execution_run_id)
        if not workflow_run_id or workflow_run_id not in self._runs:
            return
        index = int(event.payload.get("index", 0))
        step_id = str(event.payload.get("step_id") or f"step-{index}")
        self._bus.publish(
            WORKFLOW_STEP_COMPLETED,
            {
                "run_id": workflow_run_id,
                "step_id": step_id,
                "index": index,
                "success": False,
            },
            source=self.name,
        )

    def _on_execution_complete(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or "")
        execution_run_id = str(event.payload.get("run_id") or "")
        workflow_run_id = request_id if request_id in self._runs else self._workflow_id_for_execution(
            execution_run_id
        )
        if not workflow_run_id or workflow_run_id not in self._runs:
            return
        run = self._runs.pop(workflow_run_id, None) or {}
        self._execution_to_workflow.pop(execution_run_id, None)
        total = int(run.get("total_steps") or len(run.get("steps") or []))
        self._bus.publish(
            WORKFLOW_COMPLETED,
            {
                "run_id": workflow_run_id,
                "workflow_id": run.get("workflow_id"),
                "steps": total,
            },
            source=self.name,
        )
        self._bus.publish(
            TELEMETRY_EVENT,
            {"name": "workflow.completed", "run_id": workflow_run_id},
            source=self.name,
        )

    def _on_execution_failed(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or "")
        execution_run_id = str(event.payload.get("run_id") or "")
        workflow_run_id = request_id if request_id in self._runs else self._workflow_id_for_execution(
            execution_run_id
        )
        if not workflow_run_id or workflow_run_id not in self._runs:
            return
        self._runs.pop(workflow_run_id, None)
        self._execution_to_workflow.pop(execution_run_id, None)
        self._bus.publish(
            WORKFLOW_FAILED,
            {
                "run_id": workflow_run_id,
                "error": str(event.payload.get("error") or "execution failed"),
            },
            source=self.name,
        )
