"""Supervised agent runtime — bus-native spawn/task/terminate (Track 7 demo)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION, build_workspace_context
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    AGENT_CANCEL_REQUEST,
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
    COMMAND_ROUTED,
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
from ai_command_center.services.base import BaseService
from ai_command_center.core.events.intents import INTENT_AGENT

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


class AgentRuntimeService(BaseService):
    """Publishes agent lifecycle events; routes supervised agents via bus only."""

    name = "agent_runtime"
    _MAX_STEPS = 8

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._active: dict[str, dict[str, object]] = {}
        self._pending_spawns: dict[str, dict[str, object]] = {}
        self._pipelines: dict[str, dict[str, object]] = {}

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
            self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed)
        )
        self._unsubscribers.append(
            self._bus.subscribe(PERMISSION_CHECK_RESULT, self._on_permission_result)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_RESULT, self._on_tool_result)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_FAILED, self._on_tool_failed)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._active.clear()
        self._pending_spawns.clear()
        self._pipelines.clear()

    def _telemetry(self, name: str, payload: dict[str, object]) -> None:
        self._bus.publish(
            TELEMETRY_EVENT,
            {"name": name, **payload},
            source=self.name,
        )

    @staticmethod
    def _is_demo_task(task: str) -> bool:
        normalized = task.strip().lower()
        if normalized in _DEMO_TASKS:
            return True
        return normalized.startswith("demo:")

    @staticmethod
    def _demo_tool_commands(task: str) -> list[str]:
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
    def _resolve_spawn_task(task: str, *, spawn_role: str = "") -> str:
        role_key = (spawn_role or task).strip().lower()
        mapped = _SPAWN_ROLE_TASKS.get(role_key)
        if mapped:
            return mapped
        return task.strip()

    @staticmethod
    def _is_multi_demo_task(task: str, spawn_mode: str = "") -> bool:
        normalized = task.strip().lower()
        if spawn_mode == "multi":
            return normalized in {"", "multi-demo", "multi", "demo"}
        return normalized in {"multi-demo", "multi agent demo", "multi-agent demo"}

    @staticmethod
    def _is_pipeline_demo_task(task: str, spawn_mode: str = "") -> bool:
        normalized = task.strip().lower()
        if spawn_mode == "pipeline":
            return normalized in {"", "pipeline-demo", "pipeline demo", "demo", "pipeline"}
        return normalized in {"pipeline-demo", "pipeline demo", "agents pipeline demo"}

    def _on_command_routed(self, event: Event) -> None:
        if event.source != "command_router":
            return
        if event.payload.get("intent") != INTENT_AGENT:
            return
        args = event.payload.get("args") or {}
        task = str(args.get("task", "demo")).strip() or "demo"
        spawn_mode = str(args.get("spawn_mode", "single"))
        request_id = str(event.payload.get("request_id") or uuid.uuid4().hex)
        workspace_id = args.get("workspace_id")
        workspace_entity_id = args.get("workspace_entity_id")
        if self._is_pipeline_demo_task(task, spawn_mode):
            self._start_pipeline_demo(request_id, workspace_id, workspace_entity_id)
            return
        if self._is_multi_demo_task(task, spawn_mode):
            self._publish_multi_spawn(request_id, workspace_id, workspace_entity_id)
            return
        spawn_role = str(args.get("spawn_role", "")).strip()
        resolved_task = self._resolve_spawn_task(task, spawn_role=spawn_role)
        agent_id = ""
        if spawn_role:
            agent_id = f"{spawn_role.lower()}-{uuid.uuid4().hex[:8]}"
        self._bus.publish(
            AGENT_SPAWN_REQUEST,
            {
                "task": resolved_task,
                "request_id": request_id,
                "workspace_id": workspace_id,
                "workspace_entity_id": workspace_entity_id,
                "spawn_role": spawn_role,
                **({"agent_id": agent_id} if agent_id else {}),
            },
                source=self.name,
            )

    def _start_pipeline_demo(
        self,
        request_id: str,
        workspace_id: object,
        workspace_entity_id: object,
    ) -> None:
        pipeline_id = f"pipeline-{uuid.uuid4().hex[:10]}"
        stages = list(_PIPELINE_DEMO_STAGES)
        planned_tools = [f"shell: {task.split(':', 1)[-1].strip()}" for _, task in stages]
        self._pipelines[pipeline_id] = {
            "request_id": request_id,
            "workspace_id": workspace_id,
            "workspace_entity_id": workspace_entity_id,
            "stage_index": 0,
            "stages": stages,
            "current_agent_id": "",
        }
        self._bus.publish(
            AGENT_PIPELINE_STARTED,
            {
                "pipeline_id": pipeline_id,
                "request_id": request_id,
                "stage": stages[0][0],
                "total_stages": len(stages),
                "workspace_id": workspace_id,
            },
            source=self.name,
        )
        self._publish_pipeline_plan(pipeline_id, stages[0][0], [planned_tools[0]])
        self._publish_pipeline_stage(pipeline_id, stages[0][0], index=0)
        self._spawn_pipeline_stage(pipeline_id, index=0)

    def _publish_pipeline_plan(
        self, pipeline_id: str, stage: str, planned_tools: list[str]
    ) -> None:
        self._bus.publish(
            AGENT_PIPELINE_PLANNED,
            {
                "pipeline_id": pipeline_id,
                "stage": stage,
                "planned_tools": planned_tools,
                "planner": "stub",
            },
            source=self.name,
        )

    def _publish_pipeline_stage(
        self, pipeline_id: str, stage: str, *, index: int
    ) -> None:
        self._bus.publish(
            AGENT_PIPELINE_STAGE,
            {"pipeline_id": pipeline_id, "stage": stage, "index": index},
            source=self.name,
        )

    def _spawn_pipeline_stage(self, pipeline_id: str, *, index: int) -> None:
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            return
        stages = list(pipeline.get("stages") or [])
        if index >= len(stages):
            return
        role, role_task = stages[index]
        agent_id = f"{role}-{uuid.uuid4().hex[:8]}"
        pipeline["current_agent_id"] = agent_id
        pipeline["stage_index"] = index
        self._bus.publish(
            AGENT_SPAWN_REQUEST,
            {
                "agent_id": agent_id,
                "task": role_task,
                "request_id": f"{pipeline.get('request_id', pipeline_id)}-{role}",
                "workspace_id": pipeline.get("workspace_id"),
                "workspace_entity_id": pipeline.get("workspace_entity_id"),
                "spawn_role": role,
                "pipeline_id": pipeline_id,
                "pipeline_stage_index": index,
            },
            source=self.name,
        )

    def _advance_pipeline(self, pipeline_id: str, completed_agent_id: str) -> None:
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            return
        if str(pipeline.get("current_agent_id", "")) != completed_agent_id:
            return
        stages = list(pipeline.get("stages") or [])
        next_index = int(pipeline.get("stage_index", 0)) + 1
        if next_index >= len(stages):
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
            return
        role, role_task = stages[next_index]
        planned = [f"shell: {role_task.split(':', 1)[-1].strip()}"]
        self._publish_pipeline_plan(pipeline_id, role, planned)
        self._publish_pipeline_stage(pipeline_id, role, index=next_index)
        self._spawn_pipeline_stage(pipeline_id, index=next_index)

    def _publish_multi_spawn(
        self,
        request_id: str,
        workspace_id: object,
        workspace_entity_id: object,
    ) -> None:
        for role, role_task in _MULTI_DEMO_ROLES:
            agent_id = f"{role}-{uuid.uuid4().hex[:8]}"
            self._bus.publish(
                AGENT_SPAWN_REQUEST,
                {
                    "agent_id": agent_id,
                    "task": role_task,
                    "request_id": f"{request_id}-{role}",
                    "workspace_id": workspace_id,
                    "workspace_entity_id": workspace_entity_id,
                    "spawn_role": role,
                },
                source=self.name,
            )

    def _on_spawn_request(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id") or uuid.uuid4().hex)
        request_id = str(event.payload.get("request_id") or uuid.uuid4().hex)
        workspace_id = event.payload.get("workspace_id")
        workspace_entity_id = event.payload.get("workspace_entity_id")
        spawn_role = str(event.payload.get("spawn_role", "")).strip()
        pipeline_id = str(event.payload.get("pipeline_id", "")).strip()
        task = str(event.payload.get("task", "")).strip()
        task = self._resolve_spawn_task(task, spawn_role=spawn_role)
        check_id = uuid.uuid4().hex
        permissions = [Permission.USE_AI.value]
        if self._is_demo_task(task):
            permissions.append(Permission.LAUNCH_TOOL.value)
        self._pending_spawns[check_id] = {
            "agent_id": agent_id,
            "request_id": request_id,
            "workspace_id": workspace_id,
            "workspace_entity_id": workspace_entity_id,
            "spawn_role": spawn_role,
            "task": task,
            "pipeline_id": pipeline_id,
        }
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
        self._start_agent(pending)

    def _start_agent(self, pending: dict[str, object]) -> None:
        agent_id = str(pending.get("agent_id", ""))
        request_id = str(pending.get("request_id", ""))
        workspace_id = pending.get("workspace_id")
        workspace_entity_id = pending.get("workspace_entity_id")
        spawn_role = str(pending.get("spawn_role", "")).strip()
        task = str(pending.get("task", "")).strip()
        demo_mode = self._is_demo_task(task)
        self._active[agent_id] = {
            "request_id": request_id,
            "task": task,
            "steps": 0,
            "state": AgentState.RUNNING.value,
            "demo_mode": demo_mode,
            "demo_commands": self._demo_tool_commands(task) if demo_mode else [],
            "demo_index": 0,
            "workspace_id": workspace_id,
            "workspace_entity_id": workspace_entity_id,
            "spawn_role": spawn_role,
            "pipeline_id": str(pending.get("pipeline_id", "")).strip(),
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
        self._bus.publish(
            AGENT_SPAWNED,
            spawned_payload,
            source=self.name,
        )
        _logger.info("agent.spawned agent_id=%s request_id=%s", agent_id, request_id)
        self._telemetry("agent.spawned", {"agent_id": agent_id, "request_id": request_id})

        if demo_mode:
            self._run_demo_tool(agent_id, request_id, task)
            return

        if task:
            self._bus.publish(
                AGENT_TASK_REQUEST,
                {"agent_id": agent_id, "request_id": request_id, "task": task},
                source=self.name,
            )

    def _run_demo_tool(self, agent_id: str, request_id: str, task: str) -> None:
        entry = self._active.get(agent_id)
        if entry is None:
            return
        commands = list(entry.get("demo_commands") or self._demo_tool_commands(task))
        if not commands:
            commands = [_DEMO_TOOL_COMMAND]
        entry["demo_commands"] = commands
        entry["demo_index"] = 0
        self._invoke_demo_tool(agent_id, request_id, commands[0])

    def _invoke_demo_tool(self, agent_id: str, request_id: str, command: str) -> None:
        invoke_id = uuid.uuid4().hex
        entry = self._active.get(agent_id)
        if entry is None:
            return
        entry["invoke_id"] = invoke_id
        entry["state"] = AgentState.WAITING.value
        demo_index = int(entry.get("demo_index", 0))
        workspace_context = build_workspace_context(
            workspace_id=entry.get("workspace_id"),
            entity_id=entry.get("workspace_entity_id"),
        )
        self._bus.publish(
            AGENT_TASK_REQUEST,
            {
                "agent_id": agent_id,
                "request_id": request_id,
                "task": f"tool:{command}",
                "steps": demo_index + 1,
            },
            source=self.name,
        )
        self._bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": invoke_id,
                "tool": "shell",
                "args": {"command": command},
                "agent_id": agent_id,
                "request_id": request_id,
                "actor_type": "agent",
                "workspace_context": workspace_context,
            },
            source=self.name,
        )

    def _on_tool_result(self, event: Event) -> None:
        invoke_id = str(event.payload.get("invoke_id", ""))
        if not invoke_id:
            return
        for agent_id, entry in list(self._active.items()):
            if str(entry.get("invoke_id", "")) != invoke_id:
                continue
            request_id = str(entry.get("request_id", ""))
            if not event.payload.get("success"):
                error = str(event.payload.get("error") or "tool failed")
                self._terminate(agent_id, error=error)
                return

            output = str(event.payload.get("output", ""))
            self._bus.publish(
                AGENT_TASK_COMPLETE,
                {
                    "agent_id": agent_id,
                    "request_id": request_id,
                    "status": "complete",
                    "output": output,
                },
                source=self.name,
            )

            if entry.get("demo_mode"):
                commands = list(entry.get("demo_commands") or [])
                next_index = int(entry.get("demo_index", 0)) + 1
                if next_index < len(commands) and next_index < _MAX_DEMO_TOOLS:
                    entry["demo_index"] = next_index
                    entry["steps"] = int(entry.get("steps", 0)) + 1
                    self._invoke_demo_tool(agent_id, request_id, commands[next_index])
                    return

            pipeline_id = str(entry.get("pipeline_id", "")).strip()
            if pipeline_id:
                self._advance_pipeline(pipeline_id, agent_id)

            self._terminate(agent_id)
            break

    def _on_tool_failed(self, event: Event) -> None:
        invoke_id = str(event.payload.get("invoke_id", ""))
        if not invoke_id:
            return
        for agent_id, entry in list(self._active.items()):
            if str(entry.get("invoke_id", "")) != invoke_id:
                continue
            error = str(event.payload.get("message") or event.payload.get("error") or "tool failed")
            self._terminate(agent_id, error=error)
            break

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
