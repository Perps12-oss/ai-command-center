"""EventBus-driven sequential workflow engine (W0/W1 skeleton)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    TELEMETRY_EVENT,
    TOOL_INVOKE,
    TOOL_RESULT,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_START,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)


class WorkflowEngineService(BaseService):
    """Runs linear tool-step workflows via tool.invoke / tool.result."""

    name = "workflow_engine"
    _MAX_STEPS = 16

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._runs: dict[str, dict[str, Any]] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(WORKFLOW_START, self._on_workflow_start)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_RESULT, self._on_tool_result)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._runs.clear()

    def _on_workflow_start(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id") or uuid.uuid4().hex)
        steps = list(event.payload.get("steps") or [])
        if not steps:
            self._bus.publish(
                WORKFLOW_FAILED,
                {"run_id": run_id, "error": "workflow has no steps"},
                source=self.name,
            )
            return
        workflow_id = str(event.payload.get("workflow_id") or "")
        self._runs[run_id] = {"steps": steps, "index": 0, "workflow_id": workflow_id}
        _logger.info("workflow.start run_id=%s steps=%d", run_id, len(steps))
        self._bus.publish(
            WORKFLOW_STARTED,
            {
                "run_id": run_id,
                "workflow_id": workflow_id,
                "total_steps": len(steps),
            },
            source=self.name,
        )
        self._dispatch_step(run_id)

    def _dispatch_step(self, run_id: str) -> None:
        run = self._runs.get(run_id)
        if run is None:
            return
        index = int(run["index"])
        steps: list[dict[str, Any]] = run["steps"]
        if index >= len(steps):
            self._runs.pop(run_id, None)
            self._bus.publish(
                WORKFLOW_COMPLETED,
                {"run_id": run_id, "workflow_id": run.get("workflow_id"), "steps": len(steps)},
                source=self.name,
            )
            self._bus.publish(
                TELEMETRY_EVENT,
                {"name": "workflow.completed", "run_id": run_id},
                source=self.name,
            )
            return
        if index >= self._MAX_STEPS:
            self._fail(run_id, "max workflow steps exceeded")
            return
        step = steps[index]
        step_id = str(step.get("id") or f"step-{index}")
        step_type = str(step.get("type") or "tool")
        self._bus.publish(
            WORKFLOW_STEP_STARTED,
            {"run_id": run_id, "step_id": step_id, "index": index, "type": step_type},
            source=self.name,
        )
        if step_type != "tool":
            self._fail(run_id, f"unsupported step type: {step_type}")
            return
        tool_name = str(step.get("tool") or "")
        args = dict(step.get("args") or {})
        if not tool_name:
            self._fail(run_id, "tool step missing tool name")
            return
        self._bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": uuid.uuid4().hex,
                "run_id": run_id,
                "step_id": step_id,
                "tool": tool_name,
                "args": args,
            },
            source=self.name,
        )

    def _on_tool_result(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id") or "")
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        index = int(run["index"])
        step_id = str(event.payload.get("step_id") or f"step-{index}")
        success = bool(event.payload.get("success", True))
        self._bus.publish(
            WORKFLOW_STEP_COMPLETED,
            {
                "run_id": run_id,
                "step_id": step_id,
                "index": index,
                "success": success,
            },
            source=self.name,
        )
        if not success:
            self._fail(run_id, str(event.payload.get("error") or "tool step failed"))
            return
        run["index"] = index + 1
        self._dispatch_step(run_id)

    def _fail(self, run_id: str, error: str) -> None:
        self._runs.pop(run_id, None)
        self._bus.publish(
            WORKFLOW_FAILED,
            {"run_id": run_id, "error": error},
            source=self.name,
        )
