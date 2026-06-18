"""Runs one tool per tool.invoke — no loops (Phase 4B)."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Callable

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import Event
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.base import BaseService

if TYPE_CHECKING:
    from ai_command_center.services.tool_registry_service import ToolRegistryService


def _run_shell_command(args: dict) -> ToolResult:
    command = str(args.get("command", "")).strip()
    if not command:
        return ToolResult(success=False, output="", error="empty shell command")
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        output = stdout or stderr
        if completed.returncode != 0 and not output:
            return ToolResult(
                success=False,
                output="",
                error=stderr or f"exit code {completed.returncode}",
            )
        return ToolResult(success=completed.returncode == 0, output=output, error=stderr or None)
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="", error="shell command timed out")
    except OSError as exc:
        return ToolResult(success=False, output="", error=str(exc))


class ToolExecutorService(BaseService):
    name = "tool_executor"

    def __init__(self, bus, registry: ToolRegistryService) -> None:
        super().__init__(bus)
        self._registry = registry
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        if self._registry.get("shell") is None:
            self._registry.register(
                ToolSpec(
                    name="shell",
                    description="Run a single shell command",
                    handler=_run_shell_command,
                )
            )
        self._unsubscribers.append(
            self._bus.subscribe("tool.invoke", self._on_tool_invoke)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_tool_invoke(self, event: Event) -> None:
        payload = event.payload
        if payload.get("contract_version") != TOOL_CONTRACT_VERSION:
            self._bus.publish(
                "tool.error",
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "message": "unsupported tool contract version",
                },
                source=self.name,
            )
            return
        tool_name = str(payload.get("tool", "")).strip()
        args = payload.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        invoke_id = str(payload.get("invoke_id", ""))

        spec = self._registry.get(tool_name)
        if spec is None:
            self._bus.publish(
                "tool.error",
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": invoke_id,
                    "tool": tool_name,
                    "message": f"unknown tool: {tool_name}",
                },
                source=self.name,
            )
            return

        result = spec.handler(args)
        topic = "tool.result" if result.success else "tool.error"
        body = result.to_payload()
        body["invoke_id"] = invoke_id
        body["tool"] = tool_name
        if not result.success and topic == "tool.error":
            body["message"] = result.error or result.output or "tool failed"
        self._bus.publish(topic, body, source=self.name)
