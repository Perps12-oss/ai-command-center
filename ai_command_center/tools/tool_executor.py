"""Tool executor contract."""

from __future__ import annotations

from typing import Any

from ai_command_center.domain.tool_execution import ToolExecution


class ToolExecutor:
    """Executes registered tools and tracks execution state."""

    def __init__(self) -> None:
        self._status: dict[str, ToolExecution] = {}

    def execute(self, tool_name: str, **inputs: Any) -> ToolExecution:
        execution = ToolExecution(tool_name=tool_name, inputs=tuple(inputs.items()), status="running")
        self._status[tool_name] = execution
        return execution

    def cancel(self, tool_name: str) -> None:
        execution = self._status.get(tool_name)
        if execution is not None:
            self._status[tool_name] = ToolExecution(
                tool_name=tool_name,
                start_time=execution.start_time,
                end_time=execution.end_time,
                status="cancelled",
                inputs=execution.inputs,
                outputs=execution.outputs,
                error=execution.error,
            )

    def get_status(self, tool_name: str) -> ToolExecution | None:
        return self._status.get(tool_name)
