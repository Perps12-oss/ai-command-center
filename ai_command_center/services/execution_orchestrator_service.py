"""Execution orchestrator — runs approved plans with permission gates (vNext L5)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION, build_workspace_context
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CAPABILITY_COMPLETE,
    CAPABILITY_ERROR,
    CAPABILITY_RUNTIME_REQUEST,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_REQUEST,
    EXECUTION_RUN_STARTED,
    EXECUTION_STEP_APPROVED,
    EXECUTION_STEP_AWAITING_APPROVAL,
    EXECUTION_STEP_COMPLETED,
    EXECUTION_STEP_FAILED,
    EXECUTION_STEP_STARTED,
    LLM_STEP_REQUEST,
    TOOL_FAILED,
    TOOL_INVOKE,
    TOOL_RESULT,
)
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

_EXTERNAL_PREFIXES = ("mcp.", "external.", "mcp:")
_LLM_CAPABILITIES = frozenset({"llm", "chat"})


def _is_external_capability(capability: str) -> bool:
    lowered = capability.lower()
    return any(lowered.startswith(prefix) for prefix in _EXTERNAL_PREFIXES)


def _is_llm_capability(capability: str) -> bool:
    return capability.strip().lower() in _LLM_CAPABILITIES


def _is_agent_capability(capability: str) -> bool:
    return capability.strip().lower().startswith("agent.")


def _step_needs_approval(step: PlanStep, *, auto_approve: bool) -> bool:
    if auto_approve:
        return False
    return bool(step.require_approval)


class ExecutionOrchestratorService(BaseService):
    """Executes planner manifests step-by-step with approval gates."""

    name = "execution_orchestrator"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._runs: dict[str, dict[str, Any]] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_RUN_REQUEST, self._on_run_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_STEP_APPROVED, self._on_step_approved)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_RESULT, self._on_tool_result)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_FAILED, self._on_tool_failed)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CAPABILITY_COMPLETE, self._on_capability_complete)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CAPABILITY_ERROR, self._on_capability_error)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._runs.clear()

    def _on_run_request(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id") or uuid.uuid4().hex)
        raw_plan = event.payload.get("plan")
        if not isinstance(raw_plan, dict):
            self._fail_run(run_id, "plan payload is required")
            return

        plan = ExecutionPlan.from_dict(raw_plan)
        if not plan.steps:
            self._fail_run(run_id, "plan has no steps")
            return

        workspace_context = event.payload.get("workspace_context")
        if not isinstance(workspace_context, dict):
            workspace_context = build_workspace_context(
                workspace_id=event.payload.get("workspace_id"),
                entity_id=event.payload.get("entity_id"),
                entity_type=event.payload.get("entity_type"),
            )

        self._runs[run_id] = {
            "plan": plan,
            "index": 0,
            "workspace_context": workspace_context,
            "request_id": str(event.payload.get("request_id", "")),
            "correlation": CorrelationContext.from_payload(event.payload).to_payload(),
            "auto_approve": bool(event.payload.get("auto_approve", False)),
            "paused": False,
            "step_outputs": [],
            "goal": plan.goal,
        }
        _logger.info("execution.run.started run_id=%s steps=%d", run_id, len(plan.steps))
        self._bus.publish(
            EXECUTION_RUN_STARTED,
            {
                "run_id": run_id,
                "request_id": event.payload.get("request_id", ""),
                "goal": plan.goal,
                "step_count": len(plan.steps),
                "correlation": self._runs[run_id]["correlation"],
            },
            source=self.name,
        )
        self._advance_run(run_id)

    def _on_step_approved(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        step_id = str(event.payload.get("step_id", "")).strip()
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if not run.get("paused"):
            return
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        current = plan.steps[index]
        if step_id and current.step_id != step_id:
            return
        run["paused"] = False
        self._dispatch_step(run_id)

    def _on_tool_result(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if run.get("paused"):
            return
        step_id = str(event.payload.get("step_id", "")).strip()
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        current = plan.steps[index]
        if current.step_id != step_id:
            return

        success = bool(event.payload.get("success", False))
        if success:
            self._complete_step(run_id, output=str(event.payload.get("output", "")))
        else:
            self._fail_step(
                run_id,
                str(event.payload.get("error") or event.payload.get("message") or "tool failed"),
            )

    def _on_tool_failed(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if run.get("paused"):
            return
        step_id = str(event.payload.get("step_id", "")).strip()
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        current = plan.steps[index]
        if step_id and current.step_id != step_id:
            return
        self._fail_step(
            run_id,
            str(event.payload.get("error") or event.payload.get("message") or "tool failed"),
        )

    def _on_capability_complete(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if run.get("paused"):
            return
        step_id = str(event.payload.get("step_id", "")).strip()
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        if plan.steps[index].step_id != step_id:
            return
        self._complete_step(run_id, output=str(event.payload.get("output", "")))

    def _on_capability_error(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if run.get("paused"):
            return
        step_id = str(event.payload.get("step_id", "")).strip()
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        if plan.steps[index].step_id != step_id:
            return
        self._fail_step(run_id, str(event.payload.get("message") or "capability failed"))

    def _advance_run(self, run_id: str) -> None:
        if run_id not in self._runs:
            return
        run = self._runs[run_id]
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            self._complete_run(run_id)
            return

        step = plan.steps[index]
        auto_approve = bool(run.get("auto_approve", False))
        self._bus.publish(
            EXECUTION_STEP_STARTED,
            {
                "run_id": run_id,
                "step_id": step.step_id,
                "capability": step.capability,
                "index": index,
            },
            source=self.name,
        )

        if _step_needs_approval(step, auto_approve=auto_approve):
            run["paused"] = True
            self._bus.publish(
                EXECUTION_STEP_AWAITING_APPROVAL,
                {
                    "run_id": run_id,
                    "step_id": step.step_id,
                    "capability": step.capability,
                    "require_approval": True,
                },
                source=self.name,
            )
            return

        self._dispatch_step(run_id)

    def _dispatch_step(self, run_id: str) -> None:
        if run_id not in self._runs:
            return
        run = self._runs[run_id]
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        step = plan.steps[index]
        workspace_context = dict(run.get("workspace_context") or {})
        invoke_id = uuid.uuid4().hex
        request_id = str(run.get("request_id") or invoke_id)

        if _is_llm_capability(step.capability):
            self._bus.publish(
                LLM_STEP_REQUEST,
                {
                    "request_id": request_id,
                    "run_id": run_id,
                    "step_id": step.step_id,
                    "capability": "llm",
                    "args": dict(step.args),
                    "prompt": str(step.args.get("prompt") or plan.goal),
                    "workspace_context": workspace_context,
                    "command_payload": {
                        "request_id": request_id,
                        "workspace_id": workspace_context.get("workspace_id", ""),
                        "workspace_entity_id": workspace_context.get("entity_id", ""),
                        "workspace_entity_type": workspace_context.get("entity_type", ""),
                        "args": dict(step.args),
                    },
                },
                source=self.name,
            )
            return

        if _is_external_capability(step.capability):
            provider_id = str(step.args.get("provider_id") or "mcp").strip() or "mcp"
            self._bus.publish(
                CAPABILITY_RUNTIME_REQUEST,
                {
                    "request_id": invoke_id,
                    "run_id": run_id,
                    "step_id": step.step_id,
                    "kind": CapabilityKind.AUTOMATION.value,
                    "provider_id": provider_id,
                    "capability": step.capability,
                    "args": dict(step.args),
                    "workspace_id": workspace_context.get("workspace_id", ""),
                },
                source=self.name,
            )
            return

        if _is_agent_capability(step.capability):
            self._dispatch_agent_step(
                run_id=run_id,
                step=step,
                invoke_id=invoke_id,
                request_id=request_id,
                workspace_context=workspace_context,
                plan_goal=plan.goal,
            )
            return

        actor_type = str(step.args.get("actor_type") or "user")
        self._bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": invoke_id,
                "tool": step.capability,
                "args": {
                    k: v
                    for k, v in dict(step.args).items()
                    if k not in {"actor_type", "workflow_run_id", "workflow_id"}
                },
                "run_id": run_id,
                "step_id": step.step_id,
                "actor_type": actor_type,
                "workspace_context": workspace_context,
                **(
                    {"workflow_run_id": step.args["workflow_run_id"]}
                    if step.args.get("workflow_run_id")
                    else {}
                ),
            },
            source=self.name,
        )

    def _dispatch_agent_step(
        self,
        *,
        run_id: str,
        step: PlanStep,
        invoke_id: str,
        request_id: str,
        workspace_context: dict[str, Any],
        plan_goal: str,
    ) -> None:
        """Exclusive TOOL_INVOKE publisher for agent.* plan steps."""
        capability = step.capability.strip().lower()
        args = dict(step.args)

        if capability == "agent.task":
            from ai_command_center.core.events.topics import UI_COMMAND

            task = str(args.get("task") or plan_goal).strip()
            payload: dict[str, Any] = {
                "text": task,
                "agent_id": args.get("agent_id"),
                "request_id": request_id,
            }
            if workspace_context.get("workspace_id"):
                payload["workspace_id"] = workspace_context["workspace_id"]
            self._bus.publish(UI_COMMAND, payload, source=self.name)
            self._complete_step(run_id, output=f"agent.task dispatched: {task}")
            return

        tool_name = str(args.get("tool") or "shell").strip() or "shell"
        tool_args = dict(args.get("tool_args") or {})
        if not tool_args and "command" in args:
            tool_args = {"command": args.get("command")}
        agent_id = str(args.get("agent_id") or "")
        self._bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": invoke_id,
                "tool": tool_name,
                "args": tool_args,
                "run_id": run_id,
                "step_id": step.step_id,
                "actor_type": "agent",
                "agent_id": agent_id,
                "request_id": request_id,
                "spawn_role": str(args.get("spawn_role") or ""),
                "task": str(args.get("task") or ""),
                "pipeline_id": str(args.get("pipeline_id") or ""),
                "workspace_context": workspace_context,
            },
            source=self.name,
        )

    def _complete_step(self, run_id: str, *, output: str = "") -> None:
        if run_id not in self._runs:
            return
        run = self._runs[run_id]
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        step = plan.steps[index]
        outputs = list(run.get("step_outputs") or [])
        outputs.append(
            {
                "step_id": step.step_id,
                "capability": step.capability,
                "output": output,
                "success": True,
            }
        )
        run["step_outputs"] = outputs
        self._bus.publish(
            EXECUTION_STEP_COMPLETED,
            {
                "run_id": run_id,
                "step_id": step.step_id,
                "capability": step.capability,
                "output": output,
                "index": index,
            },
            source=self.name,
        )
        run["index"] = index + 1
        self._advance_run(run_id)

    def _fail_step(self, run_id: str, error: str) -> None:
        if run_id not in self._runs:
            return
        run = self._runs[run_id]
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        step = plan.steps[index]
        outputs = list(run.get("step_outputs") or [])
        outputs.append(
            {
                "step_id": step.step_id,
                "capability": step.capability,
                "output": "",
                "success": False,
                "error": error,
            }
        )
        run["step_outputs"] = outputs
        self._bus.publish(
            EXECUTION_STEP_FAILED,
            {
                "run_id": run_id,
                "step_id": step.step_id,
                "capability": step.capability,
                "error": error,
                "index": index,
            },
            source=self.name,
        )
        self._fail_run(run_id, error)

    def _complete_run(self, run_id: str) -> None:
        run = self._runs.pop(run_id, None)
        request_id = str(run.get("request_id", "")) if run else ""
        correlation = dict(run.get("correlation") or {}) if run else {}
        plan = run.get("plan") if run else None
        self._bus.publish(
            EXECUTION_RUN_COMPLETE,
            {
                "run_id": run_id,
                "request_id": request_id,
                "correlation": correlation,
                "goal": getattr(plan, "goal", "") if plan else str(run.get("goal", "") if run else ""),
                "success": True,
                "step_outputs": list(run.get("step_outputs") or []) if run else [],
                "plan": plan.to_dict() if isinstance(plan, ExecutionPlan) else {},
                "workspace_context": dict(run.get("workspace_context") or {}) if run else {},
            },
            source=self.name,
        )

    def _fail_run(self, run_id: str, error: str) -> None:
        run = self._runs.pop(run_id, None)
        request_id = str(run.get("request_id", "")) if run else ""
        correlation = dict(run.get("correlation") or {}) if run else {}
        plan = run.get("plan") if run else None
        self._bus.publish(
            EXECUTION_RUN_FAILED,
            {
                "run_id": run_id,
                "request_id": request_id,
                "error": error,
                "correlation": correlation,
                "goal": getattr(plan, "goal", "") if plan else "",
                "success": False,
                "step_outputs": list(run.get("step_outputs") or []) if run else [],
                "plan": plan.to_dict() if isinstance(plan, ExecutionPlan) else {},
                "workspace_context": dict(run.get("workspace_context") or {}) if run else {},
            },
            source=self.name,
        )
