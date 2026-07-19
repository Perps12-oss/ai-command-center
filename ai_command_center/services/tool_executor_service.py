"""Runs one tool per tool.invoke by delegating to ToolExecutor (Phase 4B)."""

from __future__ import annotations

import logging
import subprocess
import threading
import uuid
from typing import TYPE_CHECKING, Callable
from uuid import UUID

from ai_command_center.core.command_sandbox import CommandSandbox, SecurityError
from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION, is_valid_workspace_context
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    TIMELINE_RECORD_REQUEST,
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
        self._ensure_builtin_tools()
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_INVOKE, self._on_tool_invoke)
        )

    def _ensure_builtin_tools(self) -> None:
        from ai_command_center.orchestration.capability_tools import (
            run_calendar_event_create,
            run_calendar_query,
            run_launch_application,
            run_system_time_query,
        )

        builtins = (
            ToolSpec(
                name="shell",
                description="Run a single shell command",
                handler=_run_shell_command,
            ),
            ToolSpec(
                name="launch_application",
                description="Launch a whitelisted desktop application",
                handler=run_launch_application,
            ),
            ToolSpec(
                name="system_time_query",
                description="Query the current system time",
                handler=run_system_time_query,
            ),
            ToolSpec(
                name="calendar_query",
                description="Query calendar events",
                handler=run_calendar_query,
            ),
            ToolSpec(
                name="calendar_event_create",
                description="Create a calendar event",
                handler=run_calendar_event_create,
            ),
        )
        for spec in builtins:
            if self._registry_get(spec.name) is None:
                if hasattr(self._registry, "register_tool"):
                    self._registry.register_tool(spec)
                elif hasattr(self._registry, "register"):
                    self._registry.register(spec)

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

    @staticmethod
    def _workspace_context(payload: dict) -> dict[str, str]:
        raw = payload.get("workspace_context")
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items() if v is not None and str(v).strip()}
        return {}

    @staticmethod
    def _timeline_entity_id(workspace_context: dict[str, str]) -> str | None:
        for key in ("entity_id", "workspace_id"):
            raw = str(workspace_context.get(key, "")).strip()
            if not raw:
                continue
            try:
                UUID(raw)
            except ValueError:
                continue
            return raw
        return None

    def _record_tool_timeline(
        self,
        workspace_context: dict[str, str],
        *,
        tool_name: str,
        invoke_id: str,
        success: bool,
        output: str = "",
        error: str | None = None,
    ) -> None:
        workspace_id = str(workspace_context.get("workspace_id", "")).strip()
        if not workspace_id:
            return
        entity_id = self._timeline_entity_id(workspace_context)
        entity_type = str(workspace_context.get("entity_type", "")).strip() or None
        timeline_payload: dict[str, object] = {
            "request_id": uuid.uuid4().hex,
            "event_type": "tool.completed" if success else "tool.failed",
            "payload": {
                "tool": tool_name,
                "invoke_id": invoke_id,
                "workspace_id": workspace_id,
                "success": success,
                "output": output[:500] if output else "",
                "error": error or "",
            },
        }
        if entity_id:
            timeline_payload["entity_id"] = entity_id
            if entity_type:
                timeline_payload["entity_type"] = entity_type
        self._bus.publish(
            TIMELINE_RECORD_REQUEST,
            timeline_payload,
            source=self.name,
        )

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
        actor_type = str(payload.get("actor_type", "user")).strip() or "user"
        if actor_type != "user" and not is_valid_workspace_context(
            payload.get("workspace_context")
        ):
            invoke_id = str(payload.get("invoke_id", ""))
            self._bus.publish(
                TOOL_FAILED,
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": invoke_id,
                    "tool": str(payload.get("tool", "")),
                    "message": "non-user tool.invoke requires workspace_context",
                    "run_id": payload.get("run_id"),
                    "step_id": payload.get("step_id"),
                    "success": False,
                    "error": "missing workspace_context",
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
        agent_id = payload.get("agent_id")
        workspace_context = self._workspace_context(payload)

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
                    **({"agent_id": agent_id} if agent_id else {}),
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
                    "workspace_context": workspace_context,
                    **({"agent_id": agent_id} if agent_id else {}),
                },
                source=self.name,
            )
            self._record_tool_timeline(
                workspace_context,
                tool_name=tool_name,
                invoke_id=invoke_id,
                success=False,
                error=error,
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
                "workspace_context": workspace_context,
                **({"agent_id": agent_id} if agent_id else {}),
            },
            source=self.name,
        )
        self._record_tool_timeline(
            workspace_context,
            tool_name=tool_name,
            invoke_id=invoke_id,
            success=True,
            output=str(output),
            error=execution.error,
        )
        self._bus.publish(
            TOOL_COMPLETED,
            {"tool": tool_name, "invoke_id": invoke_id},
            source=self.name,
        )
