"""Runs one tool per tool.invoke by delegating to ToolExecutor (Phase 4B)."""

from __future__ import annotations

import logging
import subprocess
import threading
from typing import TYPE_CHECKING, Callable
from uuid import UUID

from ai_command_center.core.command_sandbox import CommandSandbox, SecurityError
from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    TOOL_COMPLETED,
    TOOL_FAILED,
    TOOL_INVOKE,
    TOOL_RESULT,
    TOOL_STARTED,
)
from ai_command_center.core.permission.permission import Permission, PermissionContext
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.base import BaseService
from ai_command_center.tools.tool_executor import ToolExecutor
from ai_command_center.tools.tool_registry import ToolRegistry

if TYPE_CHECKING:
    from ai_command_center.core.permission.permission_service import PermissionService

logger = logging.getLogger(__name__)

_SANDBOX = CommandSandbox()
_active_shell_proc: subprocess.Popen[str] | None = None
_active_shell_lock = threading.Lock()


def cancel_active_shell() -> bool:
    """Kill the in-flight shell subprocess, if any."""
    global _active_shell_proc
    with _active_shell_lock:
        proc = _active_shell_proc
    if proc is None or proc.poll() is not None:
        return False
    try:
        proc.kill()
        proc.wait(timeout=2.0)
        return True
    except Exception:
        logger.exception("failed to kill active shell subprocess")
        return False


def _run_shell_command(args: dict) -> ToolResult:
    global _active_shell_proc
    command = str(args.get("command", "")).strip()
    if not command:
        return ToolResult(success=False, output="", error="empty shell command")
    try:
        argv = _SANDBOX.validate_command(command)
    except SecurityError as exc:
        logger.warning("shell command rejected by sandbox: %s", exc)
        return ToolResult(success=False, output="", error=str(exc))
    try:
        with _active_shell_lock:
            proc = subprocess.Popen(
                argv,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _active_shell_proc = proc
        try:
            stdout, stderr = proc.communicate(timeout=30)
        finally:
            with _active_shell_lock:
                if _active_shell_proc is proc:
                    _active_shell_proc = None
        completed_stdout = (stdout or "").strip()
        completed_stderr = (stderr or "").strip()
        output = completed_stdout or completed_stderr
        if proc.returncode != 0 and not output:
            return ToolResult(
                success=False,
                output="",
                error=completed_stderr or f"exit code {proc.returncode}",
            )
        return ToolResult(
            success=proc.returncode == 0,
            output=output,
            error=completed_stderr or None,
        )
    except subprocess.TimeoutExpired:
        cancel_active_shell()
        return ToolResult(success=False, output="", error="shell command timed out")
    except OSError as exc:
        return ToolResult(success=False, output="", error=str(exc))


class ToolExecutorService(BaseService):
    name = "tool_executor"

    def __init__(
        self,
        bus,
        registry: ToolRegistry,
        *,
        permission_service: PermissionService | None = None,
    ) -> None:
        super().__init__(bus)
        self._registry = registry
        self._permission = permission_service
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
        cancel_active_shell()
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _shell_allowed(self, payload: dict) -> bool:
        actor_type = str(payload.get("actor_type", "user")).strip() or "user"
        if actor_type == "user":
            return True
        if self._permission is None:
            logger.warning("shell tool denied for actor_type=%s: no PermissionService", actor_type)
            return False
        actor_id_raw = payload.get("actor_id")
        actor_id: UUID | None = None
        if actor_id_raw:
            try:
                actor_id = UUID(str(actor_id_raw))
            except ValueError:
                actor_id = None
        context = PermissionContext(
            entity_id=None,
            entity_type=None,
            action_id=None,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return self._permission.check(Permission.LAUNCH_TOOL.value, context)

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
        run_id = payload.get("run_id")
        step_id = payload.get("step_id")

        if tool_name == "shell" and not self._shell_allowed(payload):
            self._bus.publish(
                TOOL_FAILED,
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": invoke_id,
                    "tool": tool_name,
                    "message": "shell tool requires launch_tool permission",
                    "run_id": run_id,
                    "step_id": step_id,
                    "success": False,
                    "error": "permission denied",
                },
                source=self.name,
            )
            return

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
                    "run_id": run_id,
                    "step_id": step_id,
                    "success": False,
                    "error": error,
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
                "run_id": run_id,
                "step_id": step_id,
            },
            source=self.name,
        )
        self._bus.publish(
            TOOL_COMPLETED,
            {"tool": tool_name, "invoke_id": invoke_id},
            source=self.name,
        )
