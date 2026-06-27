"""Tool executor contract.

ToolExecutor owns only execution and status tracking. It does not publish
events; callers (e.g. ToolExecutorService) are responsible for EventBus I/O.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ai_command_center.domain.tool_execution import ToolExecution
from ai_command_center.tools.tool_registry import ToolRegistry


class ToolExecutor:
    """Executes registered tools and tracks execution state."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._status: dict[str, ToolExecution] = {}

    def _lookup(self, tool_name: str) -> Any:
        if hasattr(self._registry, "get_spec"):
            return self._registry.get_spec(tool_name)
        if hasattr(self._registry, "get"):
            return self._registry.get(tool_name)
        return None

    def execute(self, tool_name: str, **inputs: Any) -> ToolExecution:
        """Run the tool handler and record the result."""
        spec = self._lookup(tool_name)
        if spec is None:
            execution = ToolExecution(
                tool_name=tool_name,
                inputs=tuple(inputs.items()),
                status="failed",
                error=f"unknown tool: {tool_name}",
            )
            self._status[tool_name] = execution
            return execution

        start = datetime.fromtimestamp(time.time(), tz=timezone.utc)
        running = ToolExecution(
            tool_name=tool_name,
            inputs=tuple(inputs.items()),
            status="running",
            start_time=start,
        )
        self._status[tool_name] = running

        try:
            result = spec.handler(inputs)
        except Exception as exc:
            execution = ToolExecution(
                tool_name=tool_name,
                inputs=tuple(inputs.items()),
                status="failed",
                start_time=start,
                end_time=datetime.fromtimestamp(time.time(), tz=timezone.utc),
                error=str(exc),
            )
            self._status[tool_name] = execution
            return execution

        execution = ToolExecution(
            tool_name=tool_name,
            inputs=tuple(inputs.items()),
            status="completed" if result.success else "failed",
            start_time=start,
            end_time=datetime.fromtimestamp(time.time(), tz=timezone.utc),
            outputs=(result.output,) if result.output else (),
            error=result.error,
        )
        self._status[tool_name] = execution
        return execution

    def cancel(self, tool_name: str) -> None:
        """Mark a running execution as cancelled."""
        execution = self._status.get(tool_name)
        if execution is not None and execution.status == "running":
            self._status[tool_name] = ToolExecution(
                tool_name=tool_name,
                start_time=execution.start_time,
                end_time=datetime.fromtimestamp(time.time(), tz=timezone.utc),
                status="cancelled",
                inputs=execution.inputs,
                outputs=execution.outputs,
                error=execution.error,
            )

    def get_status(self, tool_name: str) -> ToolExecution | None:
        return self._status.get(tool_name)
