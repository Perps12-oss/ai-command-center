"""Runs one tool per tool.invoke by delegating to ToolExecutor (Phase 4B)."""

from __future__ import annotations

import shlex
import subprocess
from typing import Callable

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    TOOL_COMPLETED,
    TOOL_FAILED,
    TOOL_INVOKE,
    TOOL_RESULT,
    TOOL_STARTED,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.base import BaseService
from ai_command_center.tools.tool_executor import ToolExecutor
from ai_command_center.tools.tool_registry import ToolRegistry


def _parse_command(command: str) -> list[str] | None:
    """Parse a command string into a list of arguments for shell=False execution.

    ``shlex.split(posix=False)`` is used to preserve Windows backslashes in paths.
    Outer quotes are stripped because shlex with ``posix=False`` keeps them.
    """
    try:
        args = shlex.split(command, posix=False)
    except ValueError:
        return None
    return [arg.strip("\"'") for arg in args]


# Windows CMD shell builtins that have no standalone executable.
_WINDOWS_SHELL_BUILTINS: frozenset[str] = frozenset(
    {
        "echo",
        "dir",
        "cd",
        "type",
        "cls",
        "copy",
        "del",
        "erase",
        "md",
        "mkdir",
        "rd",
        "rmdir",
        "ren",
        "rename",
        "move",
        "set",
        "path",
        "prompt",
        "ver",
        "vol",
        "date",
        "time",
        "start",
        "exit",
        "pause",
        "goto",
        "if",
        "for",
        "call",
    }
)


def _is_windows_builtin(token: str) -> bool:
    return token.lower() in _WINDOWS_SHELL_BUILTINS


def _run_shell_command(args: dict) -> ToolResult:
    command = str(args.get("command", "")).strip()
    if not command:
        return ToolResult(success=False, output="", error="empty shell command")
    cmd_args = _parse_command(command)
    if cmd_args is None:
        return ToolResult(
            success=False,
            output="",
            error="invalid command syntax",
        )
    if not cmd_args:
        return ToolResult(
            success=False,
            output="",
            error="empty command after parsing",
        )
    use_shell = _is_windows_builtin(cmd_args[0])
    try:
        if use_shell:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        else:
            completed = subprocess.run(
                cmd_args,
                shell=False,
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
        return ToolResult(
            success=completed.returncode == 0,
            output=output,
            error=stderr or None,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="", error="shell command timed out")
    except OSError as exc:
        return ToolResult(success=False, output="", error=str(exc))


class ToolExecutorService(BaseService):
    name = "tool_executor"

    def __init__(self, bus, registry: ToolRegistry) -> None:
        super().__init__(bus)
        self._registry = registry
        self._unsubscribers: list[Callable[[], None]] = []
        self._executor = ToolExecutor(registry)

    def _on_load(self) -> None:
        if self._registry_get("shell") is None:
            spec = ToolSpec(
                name="shell",
                description="Run a single shell command",
                handler=_run_shell_command,
            )
            if hasattr(self._registry, "register_tool"):
                self._registry.register_tool(spec)
            elif hasattr(self._registry, "register"):
                self._registry.register(spec)
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_INVOKE, self._on_tool_invoke)
        )

    def _registry_get(self, name: str):
        if hasattr(self._registry, "get_spec"):
            return self._registry.get_spec(name)
        if hasattr(self._registry, "get"):
            return self._registry.get(name)
        return None

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_tool_invoke(self, event: Event) -> None:
        payload = event.payload
        if payload.get("contract_version") != TOOL_CONTRACT_VERSION:
            self._bus.publish(
                TOOL_FAILED,
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

        self._bus.publish(
            TOOL_STARTED,
            {"tool": tool_name, "invoke_id": invoke_id},
            source=self.name,
        )
        execution = self._executor.execute(tool_name, **args)

        if execution.status == "failed":
            error = execution.error or "tool failed"
            self._bus.publish(
                TOOL_FAILED,
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": invoke_id,
                    "tool": tool_name,
                    "message": error,
                },
                source=self.name,
            )
            return

        output = execution.outputs[0] if execution.outputs else ""
        self._bus.publish(
            TOOL_RESULT,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": invoke_id,
                "tool": tool_name,
                "success": True,
                "output": output,
                "error": execution.error,
            },
            source=self.name,
        )
        self._bus.publish(
            TOOL_COMPLETED,
            {"tool": tool_name, "invoke_id": invoke_id},
            source=self.name,
        )

