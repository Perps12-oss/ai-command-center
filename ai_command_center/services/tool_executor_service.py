"""Runs one tool per tool.invoke by delegating to ToolExecutor (Phase 4B).

Blocking tool bodies (shell communicate, OS launch) run on a dedicated worker
so the EventBus async dispatch thread is never held for up to 30s.
"""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

from ai_command_center.core.command_sandbox import CommandSandbox
from ai_command_center.core.sandboxed_shell import (
    cancel_active_shell,
    run_sandboxed_command,
)
from ai_command_center.core.security_policy import (
    READONLY_SHELL_ALLOWLIST,
    READONLY_SHELL_TOOL,
    is_classified,
    tier_requires_human_approval,
    tool_requires_human_approval,
)
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
_READONLY_SANDBOX = CommandSandbox(allowlist=READONLY_SHELL_ALLOWLIST)


def _run_shell_command(args: dict) -> ToolResult:
    """Generic shell — arbitrary program execution (SecurityTier.WRITE_DESTROY)."""
    return _execute_shell(args, _SANDBOX)


def _run_readonly_shell_command(args: dict) -> ToolResult:
    """Bounded read-only command runner (SecurityTier.READ).

    Uses a sandbox whose allowlist excludes every interpreter, so this tool
    cannot be turned into arbitrary execution by argument injection. That is
    what makes a READ classification defensible here and not for ``shell``.
    """
    return _execute_shell(args, _READONLY_SANDBOX)


def _execute_shell(args: dict, sandbox: CommandSandbox) -> ToolResult:
    outcome = run_sandboxed_command(str(args.get("command", "")), sandbox)
    return ToolResult(
        success=bool(outcome.get("success")),
        output=str(outcome.get("output") or ""),
        error=outcome.get("error"),
    )


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
        self._exec_queue: queue.SimpleQueue[tuple[str, dict[str, Any], dict[str, Any]] | None] = (
            queue.SimpleQueue()
        )
        self._exec_thread: threading.Thread | None = None

    def _on_load(self) -> None:
        self._ensure_builtin_tools()
        self._exec_thread = threading.Thread(
            target=self._exec_worker,
            name="tool-executor-worker",
            daemon=True,
        )
        self._exec_thread.start()
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
        from ai_command_center.orchestration.workspace_launch_tools import (
            run_workspace_execute_command,
            run_workspace_open_folder,
            run_workspace_open_url,
        )

        builtins = (
            ToolSpec(
                name="shell",
                description="Run a single shell command",
                handler=_run_shell_command,
            ),
            ToolSpec(
                name=READONLY_SHELL_TOOL,
                description="Run a bounded read-only command (no interpreters)",
                handler=_run_readonly_shell_command,
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
            # G2: Workspace OS launches dispatched via TOOL_INVOKE so they are
            # receipted like any other capability. See workspace_launch_tools.
            ToolSpec(
                name="workspace_open_url",
                description="Open a workspace URL resource in the default browser",
                handler=run_workspace_open_url,
            ),
            ToolSpec(
                name="workspace_open_folder",
                description="Open a workspace folder resource in the file manager",
                handler=run_workspace_open_folder,
            ),
            ToolSpec(
                name="workspace_execute_command",
                description="Run a sandbox-validated workspace command resource",
                handler=run_workspace_execute_command,
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
        self._exec_queue.put(None)
        thread = self._exec_thread
        self._exec_thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _exec_worker(self) -> None:
        while True:
            item = self._exec_queue.get()
            if item is None:
                break
            tool_name, args, meta = item
            try:
                self._run_and_publish(tool_name, args, meta)
            except Exception:
                logger.exception("tool executor worker failed for %s", tool_name)
                self._bus.publish(
                    TOOL_FAILED,
                    {
                        "contract_version": TOOL_CONTRACT_VERSION,
                        "invoke_id": meta.get("invoke_id"),
                        "tool": tool_name,
                        "message": "tool worker failure",
                        "run_id": meta.get("run_id"),
                        "step_id": meta.get("step_id"),
                        "success": False,
                        "error": "tool worker failure",
                        "workspace_context": meta.get("workspace_context") or {},
                        **(
                            {"agent_id": meta["agent_id"]}
                            if meta.get("agent_id")
                            else {}
                        ),
                    },
                    source=self.name,
                )

    def _run_and_publish(
        self,
        tool_name: str,
        args: dict[str, Any],
        meta: dict[str, Any],
    ) -> None:
        invoke_id = str(meta.get("invoke_id") or "")
        run_id = meta.get("run_id")
        step_id = meta.get("step_id")
        agent_id = meta.get("agent_id")
        workspace_context = meta.get("workspace_context") or {}
        if not isinstance(workspace_context, dict):
            workspace_context = {}

        execution = self._executor.execute(tool_name, **args)

        if execution.status == "failed":
            error = execution.error or "tool failed"
            failed_payload: dict[str, Any] = {
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
            }
            if execution.facts:
                failed_payload["facts"] = dict(execution.facts)
            self._bus.publish(
                TOOL_FAILED,
                failed_payload,
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
        result_payload: dict[str, Any] = {
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
        }
        if execution.facts:
            result_payload["facts"] = dict(execution.facts)
        self._bus.publish(
            TOOL_RESULT,
            result_payload,
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

    def _shell_allowed(self, payload: dict) -> bool:
        actor_type = str(payload.get("actor_type", "agent")).strip() or "agent"
        if actor_type == "user" and not bool(payload.get("interactive_user")):
            actor_type = "agent"
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
        actor_type = str(payload.get("actor_type", "agent")).strip() or "agent"
        if actor_type == "user" and not bool(payload.get("interactive_user")):
            actor_type = "agent"
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

        # ADR-004: "Actions without a declared tier are rejected." Enforced here
        # independently of the orchestrator so a TOOL_INVOKE from any publisher
        # cannot execute an unclassified tool. The tier is looked up by tool
        # name in the authoritative registry and is never read from the payload,
        # so a planner cannot declare its own classification.
        _spec = self._registry_get(tool_name)
        _declared_tier = getattr(_spec, "tier", None) if _spec is not None else None
        if _declared_tier is None and not is_classified(tool_name):
            self._bus.publish(
                TOOL_FAILED,
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": invoke_id,
                    "tool": tool_name,
                    "message": f"{tool_name!r} has no authoritative SecurityTier",
                    "run_id": run_id,
                    "step_id": step_id,
                    "success": False,
                    "error": "unclassified action rejected",
                    **({"agent_id": agent_id} if agent_id else {}),
                },
                source=self.name,
            )
            return

        hitl_required = tool_requires_human_approval(tool_name)
        if _declared_tier is not None:
            hitl_required = hitl_required or tier_requires_human_approval(
                _declared_tier
            )
        if hitl_required and not bool(payload.get("human_approved")):
            self._bus.publish(
                TOOL_FAILED,
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": invoke_id,
                    "tool": tool_name,
                    "message": "WRITE_DESTROY requires explicit human approval",
                    "run_id": run_id,
                    "step_id": step_id,
                    "success": False,
                    "error": "human approval required",
                    **({"agent_id": agent_id} if agent_id else {}),
                },
                source=self.name,
            )
            return

        # Subprocess-spawning tools share the LAUNCH_TOOL permission boundary.
        # Authorization is independent of tier (ADR-022): the bounded READ
        # runner still requires permission even though it needs no approval.
        _COMMAND_TOOLS = frozenset(
            {"shell", "workspace_execute_command", READONLY_SHELL_TOOL}
        )
        if tool_name in _COMMAND_TOOLS and not self._shell_allowed(payload):
            self._bus.publish(
                TOOL_FAILED,
                {
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "invoke_id": invoke_id,
                    "tool": tool_name,
                    "message": f"{tool_name} requires launch_tool permission",
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
        job = (
            tool_name,
            dict(args),
            {
                "invoke_id": invoke_id,
                "run_id": run_id,
                "step_id": step_id,
                "agent_id": agent_id,
                "workspace_context": workspace_context,
            },
        )
        # Offload blocking execute (shell communicate / OS launch) so the
        # EventBus async dispatch thread is not held for up to 30s.
        # Tests may set ACC_TOOL_EXEC_INLINE=1 for deterministic sync completion.
        import os

        if os.environ.get("ACC_TOOL_EXEC_INLINE", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }:
            self._run_and_publish(*job)
        else:
            self._exec_queue.put(job)
