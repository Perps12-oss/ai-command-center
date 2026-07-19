"""Supervised agent runtime — capability / lifecycle handler only.

Does **not** create execution and does **not** publish TOOL_INVOKE.
Executable work is owned by ExecutionAuthority → ExecutionPlan →
EXECUTION_RUN_REQUEST → ExecutionOrchestrator.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    AGENT_CANCEL_REQUEST,
    AGENT_EXECUTION_REQUEST,
    AGENT_PIPELINE_COMPLETE,
    AGENT_PIPELINE_PLANNED,
    AGENT_PIPELINE_STAGE,
    AGENT_PIPELINE_STARTED,
    AGENT_SPAWNED,
    AGENT_SPAWN_REQUEST,
    AGENT_TASK_COMPLETE,
    AGENT_TASK_REQUEST,
    AGENT_TERMINATED,
    CHAT_COMPLETE,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
    TELEMETRY_EVENT,
    TOOL_FAILED,
    TOOL_INVOKE,
    TOOL_RESULT,
    UI_COMMAND,
)
from ai_command_center.core.permission.permission import Permission
from ai_command_center.domain.agent_session import AgentState
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

_DEMO_TASKS = frozenset({"demo", "supervised demo", "supervised-agent-demo"})
_DEMO_TOOL_COMMAND = "echo supervised-agent-demo-ok"
_MAX_DEMO_TOOLS = 3
_MULTI_DEMO_ROLES: tuple[tuple[str, str], ...] = (
    ("research", "demo: echo research-agent-ok"),
    ("review", "demo: echo review-agent-ok"),
)
_PIPELINE_DEMO_STAGES: tuple[tuple[str, str], ...] = _MULTI_DEMO_ROLES
_SPAWN_ROLE_TASKS: dict[str, str] = {
    "research": "demo: echo research-agent-ok",
    "review": "demo: echo review-agent-ok",
}
_AUTHORITY_SOURCES = frozenset({"execution_authority", "execution_orchestrator"})


class AgentRuntimeService(BaseService):
    """Agent lifecycle + plan definitions. Never publishes TOOL_INVOKE."""

    name = "agent_runtime"
    _MAX_STEPS = 8

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._active: dict[str, dict[str, object]] = {}
        self._pending_spawns: dict[str, dict[str, object]] = {}
        self._pipelines: dict[str, dict[str, object]] = {}
        self._pipeline_by_request: dict[str, str] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(AGENT_SPAWN_REQUEST, self._on_spawn_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(AGENT_TASK_REQUEST, self._on_task_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(AGENT_CANCEL_REQUEST, self._on_cancel_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CHAT_COMPLETE, self._on_chat_complete)
        )
        self._unsubscribers.append(
            self._bus.subscribe(PERMISSION_CHECK_RESULT, self._on_permission_result)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_INVOKE, self._on_tool_invoke_observe)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_RESULT, self._on_tool_result)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_FAILED, self._on_tool_failed)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_RUN_COMPLETE, self._on_execution_run_complete)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_RUN_FAILED, self._on_execution_run_failed)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._active.clear()
        self._pending_spawns.clear()
        self._pipelines.clear()
        self._pipeline_by_request.clear()

    def _telemetry(self, name: str, payload: dict[str, object]) -> None:
        self._bus.publish(
            TELEMETRY_EVENT,
            {"name": name, **payload},
            source=self.name,
        )

    # ── Plan definition API (used by ExecutionAuthority) ─────────────────────

    @staticmethod
    def is_demo_task(task: str) -> bool:
        normalized = task.strip().lower()
        if normalized in _DEMO_TASKS:
            return True
        return normalized.startswith("demo:")

    @staticmethod
    def demo_tool_commands(task: str) -> list[str]:
        normalized = task.strip()
        if normalized.lower().startswith("demo:"):
            body = normalized[5:].strip()
            if not body:
                return [_DEMO_TOOL_COMMAND]
            if ";" in body:
                parts = [part.strip() for part in body.split(";") if part.strip()]
                return parts[:_MAX_DEMO_TOOLS]
            return [body]
        return [_DEMO_TOOL_COMMAND]

    @staticmethod
    def resolve_spawn_task(task: str, *, spawn_role: str = "") -> str:
        role_key = (spawn_role or task).strip().lower()
        mapped = _SPAWN_ROLE_TASKS.get(role_key)
        if mapped:
            return mapped
        return task.strip()

    @staticmethod
    def is_multi_demo_task(task: str, spawn_mode: str = "") -> bool:
        normalized = task.strip().lower()
        if spawn_mode == "multi":
            return normalized in {"", "multi-demo", "multi", "demo"}
        return normalized in {"multi-demo", "multi agent demo", "multi-agent demo"}

    @staticmethod
    def is_pipeline_demo_task(task: str, spawn_mode: str = "") -> bool:
        normalized = task.strip().lower()
        if spawn_mode == "pipeline":
            return normalized in {"", "pipeline-demo", "pipeline demo", "demo", "pipeline"}
        return normalized in {"pipeline-demo", "pipeline demo", "agents pipeline demo"}

    @classmethod
    def build_execution_plan(
        cls,
        *,
        task: str,
        spawn_mode: str = "single",
        spawn_role: str = "",
        text: str = "",
        request_id: str = "",
    ) -> tuple[ExecutionPlan, dict[str, Any]]:
        """Build an agent.* ExecutionPlan and optional lifecycle spawn specs.

        Returns (plan, meta) where meta may include ``spawns`` and pipeline fields.
        """
        goal = text.strip() or f"agent:{task}"
        mode = (spawn_mode or "single").strip().lower()
        meta: dict[str, Any] = {"spawns": [], "pipeline_id": "", "request_id": request_id}
        steps: list[PlanStep] = []

        if cls.is_pipeline_demo_task(task, mode):
            pipeline_id = f"pipeline-{uuid.uuid4().hex[:10]}"
            meta["pipeline_id"] = pipeline_id
            meta["pipeline_stages"] = list(_PIPELINE_DEMO_STAGES)
            for role, role_task in _PIPELINE_DEMO_STAGES:
                agent_id = f"{role}-{uuid.uuid4().hex[:8]}"
                commands = cls.demo_tool_commands(role_task)
                meta["spawns"].append(
                    {
                        "agent_id": agent_id,
                        "task": role_task,
                        "spawn_role": role,
                        "pipeline_id": pipeline_id,
                        "request_id": f"{request_id}-{role}" if request_id else agent_id,
                        "expected_tools": len(commands),
                    }
                )
                for index, command in enumerate(commands):
                    steps.append(
                        PlanStep(
                            step_id=f"agent-{role}-{index}",
                            capability="agent.shell",
                            args={
                                "tool": "shell",
                                "command": command,
                                "agent_id": agent_id,
                                "spawn_role": role,
                                "task": role_task,
                                "pipeline_id": pipeline_id,
                                "actor_type": "agent",
                            },
                        )
                    )
            return ExecutionPlan(goal=goal, steps=tuple(steps)), meta

        if cls.is_multi_demo_task(task, mode):
            for role, role_task in _MULTI_DEMO_ROLES:
                agent_id = f"{role}-{uuid.uuid4().hex[:8]}"
                commands = cls.demo_tool_commands(role_task)
                meta["spawns"].append(
                    {
                        "agent_id": agent_id,
                        "task": role_task,
                        "spawn_role": role,
                        "request_id": f"{request_id}-{role}" if request_id else agent_id,
                        "expected_tools": len(commands),
                    }
                )
                for index, command in enumerate(commands):
                    steps.append(
                        PlanStep(
                            step_id=f"agent-{role}-{index}",
                            capability="agent.shell",
                            args={
                                "tool": "shell",
                                "command": command,
                                "agent_id": agent_id,
                                "spawn_role": role,
                                "task": role_task,
                                "actor_type": "agent",
                            },
                        )
                    )
            return ExecutionPlan(goal=goal, steps=tuple(steps)), meta

        resolved = cls.resolve_spawn_task(task, spawn_role=spawn_role)
        agent_id = ""
        if spawn_role:
            agent_id = f"{spawn_role.lower()}-{uuid.uuid4().hex[:8]}"
        else:
            agent_id = f"agent-{uuid.uuid4().hex[:8]}"

        if cls.is_demo_task(resolved):
            commands = cls.demo_tool_commands(resolved)
            meta["spawns"].append(
                {
                    "agent_id": agent_id,
                    "task": resolved,
                    "spawn_role": spawn_role,
                    "request_id": request_id or agent_id,
                    "expected_tools": len(commands),
                }
            )
            for index, command in enumerate(commands):
                steps.append(
                    PlanStep(
                        step_id=f"agent-step-{index + 1}",
                        capability="agent.shell",
                        args={
                            "tool": "shell",
                            "command": command,
                            "agent_id": agent_id,
                            "spawn_role": spawn_role,
                            "task": resolved,
                            "actor_type": "agent",
                        },
                    )
                )
            return ExecutionPlan(goal=goal, steps=tuple(steps)), meta

        # Non-demo: single agent.task step — Orchestrator hands off to lifecycle.
        meta["spawns"].append(
            {
                "agent_id": agent_id,
                "task": resolved,
                "spawn_role": spawn_role,
                "request_id": request_id or agent_id,
            }
        )
        steps.append(
            PlanStep(
                step_id="agent-task-1",
                capability="agent.task",
                args={
                    "task": resolved,
                    "agent_id": agent_id,
                    "spawn_role": spawn_role,
                    "actor_type": "agent",
                },
            )
        )
        return ExecutionPlan(goal=goal, steps=tuple(steps)), meta

    @classmethod
    def build_plan_from_commands(
        cls,
        *,
        agent_id: str,
        commands: list[str],
        task: str = "",
        request_id: str = "",
        spawn_role: str = "",
    ) -> ExecutionPlan:
        goal = task or f"agent:{agent_id}"
        steps = tuple(
            PlanStep(
                step_id=f"agent-step-{index + 1}",
                capability="agent.shell",
                args={
                    "tool": "shell",
                    "command": command,
                    "agent_id": agent_id,
                    "spawn_role": spawn_role,
                    "task": task,
                    "request_id": request_id,
                    "actor_type": "agent",
                },
            )
            for index, command in enumerate(commands)
            if command
        )
        return ExecutionPlan(goal=goal, steps=steps)

    # ── Spawn / permission (lifecycle only) ──────────────────────────────────

    def _on_spawn_request(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id") or uuid.uuid4().hex)
        request_id = str(event.payload.get("request_id") or uuid.uuid4().hex)
        workspace_id = event.payload.get("workspace_id")
        workspace_entity_id = event.payload.get("workspace_entity_id")
        spawn_role = str(event.payload.get("spawn_role", "")).strip()
        pipeline_id = str(event.payload.get("pipeline_id", "")).strip()
        task = str(event.payload.get("task", "")).strip()
        task = self.resolve_spawn_task(task, spawn_role=spawn_role)
        pending = {
            "agent_id": agent_id,
            "request_id": request_id,
            "workspace_id": workspace_id,
            "workspace_entity_id": workspace_entity_id,
            "spawn_role": spawn_role,
            "task": task,
            "pipeline_id": pipeline_id,
            "execute_tools": bool(event.payload.get("execute_tools", True)),
        }

        # Authority-owned spawns: lifecycle only (tools already in ExecutionPlan).
        if event.source in _AUTHORITY_SOURCES or not pending["execute_tools"]:
            self._start_agent(pending, request_execution=False)
            return

        check_id = uuid.uuid4().hex
        permissions = [Permission.USE_AI.value]
        if self.is_demo_task(task):
            permissions.append(Permission.LAUNCH_TOOL.value)
        self._pending_spawns[check_id] = pending
        self._bus.publish(
            PERMISSION_CHECK_REQUEST,
            {
                "check_id": check_id,
                "permissions": permissions,
                "actor_type": "agent",
                "actor_id": agent_id,
                "interactive": True,
                "summary": f"Agent spawn requires: {', '.join(permissions)}",
            },
            source=self.name,
        )

    def _on_permission_result(self, event: Event) -> None:
        if event.source not in {"permission_service", "ui"}:
            return
        check_id = str(event.payload.get("check_id", ""))
        pending = self._pending_spawns.pop(check_id, None)
        if pending is None:
            return
        if not event.payload.get("granted"):
            agent_id = str(pending.get("agent_id", ""))
            self._bus.publish(
                AGENT_TERMINATED,
                {
                    "agent_id": agent_id,
                    "request_id": str(pending.get("request_id", "")),
                    "state": AgentState.TERMINATED.value,
                    "error": "permission denied",
                },
                source=self.name,
            )
            self._telemetry(
                "agent.permission_denied",
                {"agent_id": agent_id, "check_id": check_id},
            )
            return
        self._start_agent(pending, request_execution=True)

    def _start_agent(
        self, pending: dict[str, object], *, request_execution: bool
    ) -> None:
        agent_id = str(pending.get("agent_id", ""))
        request_id = str(pending.get("request_id", ""))
        workspace_id = pending.get("workspace_id")
        workspace_entity_id = pending.get("workspace_entity_id")
        spawn_role = str(pending.get("spawn_role", "")).strip()
        task = str(pending.get("task", "")).strip()
        demo_mode = self.is_demo_task(task)
        expected_tools = int(pending.get("expected_tools") or 0)
        demo_commands = self.demo_tool_commands(task) if demo_mode else []
        if expected_tools <= 0 and demo_mode and request_execution:
            expected_tools = len(demo_commands) or 1
        self._active[agent_id] = {
            "request_id": request_id,
            "task": task,
            "steps": 0,
            "state": AgentState.RUNNING.value,
            "demo_mode": demo_mode,
            "demo_commands": demo_commands,
            "demo_index": 0,
            "workspace_id": workspace_id,
            "workspace_entity_id": workspace_entity_id,
            "spawn_role": spawn_role,
            "pipeline_id": str(pending.get("pipeline_id", "")).strip(),
            "pending_commands": expected_tools,
            "tools_precounted": expected_tools > 0,
        }
        spawned_payload: dict[str, object] = {
            "agent_id": agent_id,
            "request_id": request_id,
            "workspace_id": workspace_id,
            "task": task,
            "state": AgentState.SPAWNING.value,
        }
        if workspace_entity_id:
            spawned_payload["workspace_entity_id"] = workspace_entity_id
        if spawn_role:
            spawned_payload["spawn_role"] = spawn_role
        self._bus.publish(AGENT_SPAWNED, spawned_payload, source=self.name)
        _logger.info("agent.spawned agent_id=%s request_id=%s", agent_id, request_id)
        self._telemetry("agent.spawned", {"agent_id": agent_id, "request_id": request_id})

        if not request_execution:
            return

        if demo_mode:
            commands = list(self._active[agent_id].get("demo_commands") or [_DEMO_TOOL_COMMAND])
            self._active[agent_id]["pending_commands"] = len(commands)
            self._active[agent_id]["tools_precounted"] = True
            self._bus.publish(
                AGENT_EXECUTION_REQUEST,
                {
                    "agent_id": agent_id,
                    "request_id": request_id,
                    "task": task,
                    "commands": commands,
                    "spawn_role": spawn_role,
                    "workspace_id": workspace_id,
                    "workspace_entity_id": workspace_entity_id,
                },
                source=self.name,
            )
            return

        if task:
            self._bus.publish(
                AGENT_TASK_REQUEST,
                {"agent_id": agent_id, "request_id": request_id, "task": task},
                source=self.name,
            )

    def _on_tool_invoke_observe(self, event: Event) -> None:
        """Track in-flight orchestrator tool invokes for lifecycle projection."""
        if event.source != "execution_orchestrator":
            return
        agent_id = str(event.payload.get("agent_id") or "").strip()
        if not agent_id or agent_id not in self._active:
            return
        invoke_id = str(event.payload.get("invoke_id") or "")
        entry = self._active[agent_id]
        entry["invoke_id"] = invoke_id
        entry["state"] = AgentState.WAITING.value
        if not entry.get("tools_precounted"):
            entry["pending_commands"] = int(entry.get("pending_commands", 0)) + 1

    def _on_tool_result(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id") or "").strip()
        invoke_id = str(event.payload.get("invoke_id", ""))
        entry = None
        if agent_id and agent_id in self._active:
            entry = self._active[agent_id]
        elif invoke_id:
            for aid, candidate in list(self._active.items()):
                if str(candidate.get("invoke_id", "")) == invoke_id:
                    agent_id = aid
                    entry = candidate
                    break
        if entry is None or not agent_id:
            return

        if invoke_id:
            entry["invoke_id"] = invoke_id
        # Sync bus: RESULT may beat INVOKE observe when tools aren't precounted.
        if int(entry.get("pending_commands", 0)) <= 0 and not entry.get("tools_precounted"):
            entry["pending_commands"] = 1

        request_id = str(entry.get("request_id", ""))
        if not event.payload.get("success"):
            error = str(event.payload.get("error") or "tool failed")
            self._terminate(agent_id, error=error)
            return

        output = str(event.payload.get("output", ""))
        entry["steps"] = int(entry.get("steps", 0)) + 1
        self._bus.publish(
            AGENT_TASK_COMPLETE,
            {
                "agent_id": agent_id,
                "request_id": request_id,
                "status": "complete",
                "output": output,
                "steps": entry["steps"],
            },
            source=self.name,
        )
        pending = int(entry.get("pending_commands", 1)) - 1
        entry["pending_commands"] = pending
        if pending > 0:
            return

        pipeline_id = str(entry.get("pipeline_id", "")).strip()
        if pipeline_id and pipeline_id in self._pipelines:
            self._advance_pipeline_tracking(pipeline_id, agent_id)

        self._terminate(agent_id)

    def _on_tool_failed(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id") or "").strip()
        invoke_id = str(event.payload.get("invoke_id", ""))
        if agent_id and agent_id in self._active:
            error = str(event.payload.get("message") or event.payload.get("error") or "tool failed")
            self._terminate(agent_id, error=error)
            return
        if not invoke_id:
            return
        for aid, entry in list(self._active.items()):
            if str(entry.get("invoke_id", "")) != invoke_id:
                continue
            error = str(event.payload.get("message") or event.payload.get("error") or "tool failed")
            self._terminate(aid, error=error)
            break

    def register_pipeline(
        self,
        *,
        pipeline_id: str,
        request_id: str,
        stages: list[tuple[str, str]],
    ) -> None:
        """Record pipeline metadata published by ExecutionAuthority."""
        self._pipelines[pipeline_id] = {
            "request_id": request_id,
            "stage_index": 0,
            "stages": stages,
            "completed_agents": [],
        }
        if request_id:
            self._pipeline_by_request[request_id] = pipeline_id
        self._bus.publish(
            AGENT_PIPELINE_STARTED,
            {
                "pipeline_id": pipeline_id,
                "request_id": request_id,
                "stage": stages[0][0] if stages else "",
                "total_stages": len(stages),
            },
            source=self.name,
        )
        for index, (role, role_task) in enumerate(stages):
            planned = [f"shell: {role_task.split(':', 1)[-1].strip()}"]
            self._bus.publish(
                AGENT_PIPELINE_PLANNED,
                {
                    "pipeline_id": pipeline_id,
                    "stage": role,
                    "planned_tools": planned,
                    "planner": "execution_authority",
                },
                source=self.name,
            )
            self._bus.publish(
                AGENT_PIPELINE_STAGE,
                {"pipeline_id": pipeline_id, "stage": role, "index": index},
                source=self.name,
            )

    def _advance_pipeline_tracking(self, pipeline_id: str, completed_agent_id: str) -> None:
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            return
        completed = list(pipeline.get("completed_agents") or [])
        if completed_agent_id not in completed:
            completed.append(completed_agent_id)
            pipeline["completed_agents"] = completed
        stages = list(pipeline.get("stages") or [])
        next_index = len(completed)
        if next_index < len(stages):
            role, role_task = stages[next_index]
            planned = [f"shell: {role_task.split(':', 1)[-1].strip()}"]
            self._bus.publish(
                AGENT_PIPELINE_PLANNED,
                {
                    "pipeline_id": pipeline_id,
                    "stage": role,
                    "planned_tools": planned,
                    "planner": "execution_authority",
                },
                source=self.name,
            )
            self._bus.publish(
                AGENT_PIPELINE_STAGE,
                {"pipeline_id": pipeline_id, "stage": role, "index": next_index},
                source=self.name,
            )
            return
        self._bus.publish(
            AGENT_PIPELINE_COMPLETE,
            {
                "pipeline_id": pipeline_id,
                "request_id": pipeline.get("request_id", ""),
                "status": "complete",
            },
            source=self.name,
        )
        self._pipelines.pop(pipeline_id, None)

    def _on_execution_run_complete(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or "")
        pipeline_id = self._pipeline_by_request.pop(request_id, "")
        if pipeline_id and pipeline_id in self._pipelines:
            self._bus.publish(
                AGENT_PIPELINE_COMPLETE,
                {
                    "pipeline_id": pipeline_id,
                    "request_id": request_id,
                    "status": "complete",
                },
                source=self.name,
            )
            self._pipelines.pop(pipeline_id, None)

    def _on_execution_run_failed(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or "")
        pipeline_id = self._pipeline_by_request.pop(request_id, "")
        if pipeline_id:
            self._pipelines.pop(pipeline_id, None)

    def _on_task_request(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id", ""))
        if not agent_id or agent_id not in self._active:
            return
        entry = self._active[agent_id]
        if entry.get("demo_mode"):
            return
        steps = int(entry.get("steps", 0)) + 1
        if steps > self._MAX_STEPS:
            self._terminate(agent_id, error="max agent steps exceeded")
            return
        entry["steps"] = steps
        task = str(event.payload.get("task") or entry.get("task") or "").strip()
        request_id = str(event.payload.get("request_id") or entry.get("request_id") or "")
        if not task:
            self._terminate(agent_id)
            return
        command_payload: dict[str, object] = {
            "text": task,
            "agent_id": agent_id,
            "request_id": request_id,
        }
        workspace_id = str(entry.get("workspace_id") or "").strip()
        workspace_entity_id = str(entry.get("workspace_entity_id") or "").strip()
        if workspace_id:
            command_payload["workspace_id"] = workspace_id
        if workspace_entity_id:
            command_payload["workspace_entity_id"] = workspace_entity_id
        self._bus.publish(UI_COMMAND, command_payload, source=self.name)

    def _on_chat_complete(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or "")
        if not request_id:
            return
        for agent_id, entry in list(self._active.items()):
            if entry.get("demo_mode"):
                continue
            if str(entry.get("request_id")) != request_id:
                continue
            self._bus.publish(
                AGENT_TASK_COMPLETE,
                {
                    "agent_id": agent_id,
                    "request_id": request_id,
                    "status": "complete",
                },
                source=self.name,
            )
            self._terminate(agent_id)
            break

    def _on_cancel_request(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id", ""))
        if agent_id:
            self._terminate(agent_id, error=str(event.payload.get("reason", "cancelled")))

    def _terminate(self, agent_id: str, *, error: str | None = None) -> None:
        entry = self._active.pop(agent_id, None)
        if entry is None:
            return
        request_id = str(entry.get("request_id", ""))
        payload: dict[str, object] = {
            "agent_id": agent_id,
            "request_id": request_id,
            "state": AgentState.TERMINATED.value,
        }
        if error:
            payload["error"] = error
        self._bus.publish(AGENT_TERMINATED, payload, source=self.name)
        self._telemetry("agent.terminated", payload)
