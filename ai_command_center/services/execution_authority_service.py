"""Single Execution Authority — sole creator of executable work.

Routes typed UI_COMMAND and workflow.start into ExecutionPlan → GOAL_SUBMIT_REQUEST.
Never publishes TOOL_INVOKE or LLM_REQUEST.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable
from typing import Any

from ai_command_center.core.contracts import COMMAND_ROUTED_VERSION, build_workspace_context
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.intents import (
    INTENT_AGENT,
    INTENT_CHAT,
    INTENT_MEMORY_REMEMBER,
    INTENT_MEMORY_SELECT,
    INTENT_NAVIGATE,
    INTENT_NOTE_NEW,
    INTENT_NOTE_SEARCH,
    INTENT_SHELL,
)
from ai_command_center.core.events.topics import (
    AGENT_EXECUTION_REQUEST,
    AGENT_SPAWN_REQUEST,
    COMMAND_DEFERRED,
    COMMAND_ROUTED,
    EXECUTION_AUTHORITY_DECISION,
    GOAL_SUBMIT_REQUEST,
    UI_COMMAND,
    UI_WORKSPACE_REQUIRED,
    WORKFLOW_EXECUTION_REQUEST,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.execution_decision import DecisionKind, ExecutionDecision
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
from ai_command_center.orchestration.intents.classifier import RuleBasedIntentClassifier
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.services.agent_runtime_service import AgentRuntimeService
from ai_command_center.services.base import BaseService
from ai_command_center.services.command_router_service import (
    CommandRouterService,
    _WORKSPACE_OPTIONAL_INTENTS,
)

_logger = logging.getLogger(__name__)

_LAUNCH_RE = re.compile(
    r"^\s*(?:open|launch|start)\s+(\w+)\s*$",
    re.IGNORECASE,
)

_LEGACY_INTENTS: frozenset[str] = frozenset(
    {
        INTENT_NAVIGATE,
        INTENT_NOTE_SEARCH,
        INTENT_NOTE_NEW,
        INTENT_MEMORY_REMEMBER,
        INTENT_MEMORY_SELECT,
    }
)

_ORCH_CAPABILITY: dict[OrchestrationIntent, str] = {
    OrchestrationIntent.LAUNCH_APPLICATION: "launch_application",
    OrchestrationIntent.EXECUTE_SHELL: "shell",
    OrchestrationIntent.SYSTEM_TIME_QUERY: "system_time_query",
    OrchestrationIntent.CALENDAR_QUERY: "calendar_query",
    OrchestrationIntent.CALENDAR_EVENT_CREATE: "calendar_event_create",
}


class ExecutionAuthorityService(BaseService):
    """Owns intake. Emits GOAL_SUBMIT_REQUEST / COMMAND_ROUTED — never TOOL_INVOKE."""

    name = "execution_authority"

    def __init__(
        self,
        bus,
        *,
        classifier: RuleBasedIntentClassifier | None = None,
        agent_runtime: AgentRuntimeService | None = None,
    ) -> None:
        super().__init__(bus)
        self._classifier = classifier or RuleBasedIntentClassifier()
        self._agent_runtime = agent_runtime
        self._unsubscribers: list[Callable[[], None]] = []
        self._active_workspace_id: str = ""

    def _on_load(self) -> None:
        self._unsubscribers.append(self._bus.subscribe(UI_COMMAND, self._on_ui_command))
        self._unsubscribers.append(
            self._bus.subscribe(WORKFLOW_EXECUTION_REQUEST, self._on_workflow_execution_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(AGENT_EXECUTION_REQUEST, self._on_agent_execution_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_ACTIVE, self._on_workspace_active)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_DEACTIVATED, self._on_workspace_deactivated)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_workspace_active(self, event: Event) -> None:
        self._active_workspace_id = str(event.payload.get("workspace_id", "")).strip()

    def _on_workspace_deactivated(self, event: Event) -> None:
        cleared = str(event.payload.get("workspace_id", "")).strip()
        if not cleared or cleared == self._active_workspace_id:
            self._active_workspace_id = ""

    def _resolve_active_workspace_id(self, event: Event) -> str:
        payload_ws = str(event.payload.get("workspace_id", "")).strip()
        return payload_ws or self._active_workspace_id

    def _workspace_scope(self, event: Event) -> dict[str, str]:
        scope: dict[str, str] = {}
        workspace_entity_id = str(event.payload.get("workspace_entity_id", "")).strip()
        if workspace_entity_id:
            scope["workspace_entity_id"] = workspace_entity_id
            scope["workspace_entity_type"] = str(
                event.payload.get("workspace_entity_type", "")
            )
            scope["workspace_entity_title"] = str(
                event.payload.get("workspace_entity_title", "")
            )
            for key in (
                "workspace_entity_description",
                "workspace_entity_url",
                "workspace_entity_path",
            ):
                value = str(event.payload.get(key, "")).strip()
                if value:
                    scope[key] = value
        workspace_id = self._resolve_active_workspace_id(event)
        if workspace_id:
            scope["workspace_id"] = workspace_id
        for key in (
            "selected_entity_id",
            "selected_entity_type",
            "selected_entity_title",
        ):
            value = str(event.payload.get(key, "")).strip()
            if value:
                scope[key] = value
        return scope

    def _on_ui_command(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return

        request_id = uuid.uuid4().hex
        scope = self._workspace_scope(event)
        clipboard = event.payload.get("clipboard")
        decision = self.analyze(text, clipboard=clipboard)

        self._bus.publish(
            EXECUTION_AUTHORITY_DECISION,
            {
                "request_id": request_id,
                **decision.to_payload(),
                **scope,
            },
            source=self.name,
        )

        if decision.kind is DecisionKind.LEGACY_ROUTE:
            self._publish_legacy_routed(
                request_id=request_id,
                text=text,
                intent=decision.legacy_intent,
                args=dict(decision.args),
                scope=scope,
                event=event,
            )
            return

        active_workspace_id = self._resolve_active_workspace_id(event)
        if not active_workspace_id:
            if decision.capability == "shell":
                deferred_intent = INTENT_SHELL
            elif decision.capability == "llm":
                deferred_intent = INTENT_CHAT
            elif (decision.capability or "").startswith("agent"):
                deferred_intent = INTENT_AGENT
            else:
                deferred_intent = decision.capability or INTENT_CHAT
            self._defer_no_workspace(request_id, text, deferred_intent)
            return

        if (decision.capability or "").startswith("agent"):
            self._dispatch_agent(
                request_id=request_id,
                text=text,
                decision=decision,
                scope=scope,
            )
            return

        plan = self._plan_for_decision(decision)
        self._submit_plan(
            request_id=request_id,
            text=text,
            decision=decision,
            plan=plan,
            scope=scope,
        )

    def _on_workflow_execution_request(self, event: Event) -> None:
        """WORKFLOW_EXECUTION_REQUEST → ExecutionPlan → GOAL_SUBMIT_REQUEST."""
        run_id = str(event.payload.get("run_id") or uuid.uuid4().hex)
        raw_steps = list(event.payload.get("steps") or [])
        if not raw_steps:
            return
        workflow_id = str(event.payload.get("workflow_id") or "")
        workspace_context = event.payload.get("workspace_context")
        if not isinstance(workspace_context, dict):
            workspace_context = build_workspace_context(
                workspace_id=event.payload.get("workspace_id"),
                entity_id=event.payload.get("entity_id"),
                entity_type=event.payload.get("entity_type"),
            )

        plan_steps: list[PlanStep] = []
        for index, step in enumerate(raw_steps):
            if not isinstance(step, dict):
                continue
            step_type = str(step.get("type") or "tool")
            if step_type != "tool":
                continue
            tool_name = str(step.get("tool") or "").strip()
            if not tool_name:
                continue
            step_id = str(step.get("id") or f"step-{index}")
            plan_steps.append(
                PlanStep(
                    step_id=step_id,
                    capability=tool_name,
                    args={
                        **dict(step.get("args") or {}),
                        "actor_type": "workflow",
                        "workflow_run_id": run_id,
                        "workflow_id": workflow_id,
                    },
                    require_approval=False,
                )
            )
        if not plan_steps:
            return

        plan = ExecutionPlan(
            goal=f"workflow:{workflow_id or run_id}",
            steps=tuple(plan_steps),
        )
        correlation = CorrelationContext.new(goal_id=run_id).to_payload()
        correlation["correlation_id"] = run_id
        payload: dict[str, Any] = {
            "goal_id": run_id,
            "title": plan.goal,
            "description": "workflow",
            "request_id": run_id,
            "correlation": correlation,
            "auto_approve": True,
            "workspace_context": workspace_context,
            "workspace_id": str(workspace_context.get("workspace_id") or ""),
            "plan": plan.to_dict(),
            "planner_mode": "synthetic",
            "workflow_run_id": run_id,
            "workflow_id": workflow_id,
            "authority_decision": {
                "kind": DecisionKind.ACTIONABLE.value,
                "capability": "workflow",
                "reason": "workflow_start",
                "skip_planner": True,
            },
        }
        _logger.info(
            "execution_authority.workflow request_id=%s steps=%d",
            run_id,
            len(plan_steps),
        )
        self._bus.publish(GOAL_SUBMIT_REQUEST, payload, source=self.name)

    def _on_agent_execution_request(self, event: Event) -> None:
        """Lifecycle handler handoff → ExecutionPlan → GOAL_SUBMIT (no TOOL_INVOKE)."""
        agent_id = str(event.payload.get("agent_id") or uuid.uuid4().hex)
        request_id = str(event.payload.get("request_id") or uuid.uuid4().hex)
        task = str(event.payload.get("task") or "")
        commands = [str(c) for c in (event.payload.get("commands") or []) if str(c).strip()]
        if not commands:
            commands = AgentRuntimeService.demo_tool_commands(task or "demo")
        spawn_role = str(event.payload.get("spawn_role") or "")
        plan = AgentRuntimeService.build_plan_from_commands(
            agent_id=agent_id,
            commands=commands,
            task=task,
            request_id=request_id,
            spawn_role=spawn_role,
        )
        workspace_context = build_workspace_context(
            workspace_id=event.payload.get("workspace_id"),
            entity_id=event.payload.get("workspace_entity_id"),
        )
        correlation = CorrelationContext.new(goal_id=request_id).to_payload()
        correlation["correlation_id"] = request_id
        payload: dict[str, Any] = {
            "goal_id": request_id,
            "title": plan.goal,
            "description": "agent_execution_request",
            "request_id": request_id,
            "correlation": correlation,
            "auto_approve": True,
            "workspace_context": workspace_context,
            "workspace_id": str(workspace_context.get("workspace_id") or ""),
            "plan": plan.to_dict(),
            "planner_mode": "synthetic",
            "authority_decision": {
                "kind": DecisionKind.ACTIONABLE.value,
                "capability": "agent.shell",
                "reason": "agent_execution_request",
                "skip_planner": True,
            },
        }
        self._bus.publish(GOAL_SUBMIT_REQUEST, payload, source=self.name)

    def _dispatch_agent(
        self,
        *,
        request_id: str,
        text: str,
        decision: ExecutionDecision,
        scope: dict[str, str],
    ) -> None:
        args = dict(decision.args)
        plan, meta = AgentRuntimeService.build_execution_plan(
            task=str(args.get("task") or "demo"),
            spawn_mode=str(args.get("spawn_mode") or "single"),
            spawn_role=str(args.get("spawn_role") or ""),
            text=text,
            request_id=request_id,
        )
        if not plan.steps:
            return

        pipeline_id = str(meta.get("pipeline_id") or "")
        stages = list(meta.get("pipeline_stages") or [])
        runtime = self._resolve_agent_runtime()
        if pipeline_id and stages and runtime is not None:
            runtime.register_pipeline(
                pipeline_id=pipeline_id,
                request_id=request_id,
                stages=[(str(r), str(t)) for r, t in stages],
            )

        for spawn in list(meta.get("spawns") or []):
            spawn_payload = {
                **dict(spawn),
                "workspace_id": scope.get("workspace_id"),
                "workspace_entity_id": scope.get("workspace_entity_id"),
                "execute_tools": False,
            }
            self._bus.publish(AGENT_SPAWN_REQUEST, spawn_payload, source=self.name)

        self._submit_plan(
            request_id=request_id,
            text=text,
            decision=decision,
            plan=plan,
            scope=scope,
        )

    def _resolve_agent_runtime(self) -> AgentRuntimeService | None:
        if self._agent_runtime is not None:
            return self._agent_runtime
        # Best-effort: find a started instance sharing this bus (tests / composition root).
        return None

    def _submit_plan(
        self,
        *,
        request_id: str,
        text: str,
        decision: ExecutionDecision,
        plan: ExecutionPlan | None,
        scope: dict[str, str],
    ) -> None:
        correlation = CorrelationContext.new(goal_id=request_id).to_payload()
        correlation["correlation_id"] = request_id

        workspace_context = build_workspace_context(
            workspace_id=scope.get("workspace_id"),
            entity_id=scope.get("workspace_entity_id") or scope.get("selected_entity_id"),
            entity_type=scope.get("workspace_entity_type")
            or scope.get("selected_entity_type"),
        )

        payload: dict[str, Any] = {
            "goal_id": request_id,
            "title": text,
            "description": decision.reason or decision.kind.value,
            "request_id": request_id,
            "correlation": correlation,
            "auto_approve": True,
            "workspace_context": workspace_context,
            "workspace_id": scope.get("workspace_id", ""),
            "authority_decision": decision.to_payload(),
        }
        if plan is not None and decision.skip_planner:
            payload["plan"] = plan.to_dict()
            payload["planner_mode"] = "synthetic"

        _logger.info(
            "execution_authority.dispatch request_id=%s kind=%s capability=%s skip_planner=%s",
            request_id,
            decision.kind.value,
            decision.capability,
            decision.skip_planner,
        )
        self._bus.publish(GOAL_SUBMIT_REQUEST, payload, source=self.name)

    def _defer_no_workspace(self, request_id: str, text: str, intent: str) -> None:
        deferred_payload = {
            "contract_version": COMMAND_ROUTED_VERSION,
            "request_id": request_id,
            "text": text,
            "intent": intent,
            "args": {},
            "reason": "no_active_workspace",
            "status": "deferred",
        }
        self._bus.publish(COMMAND_DEFERRED, deferred_payload, source=self.name)
        self._bus.publish(
            UI_WORKSPACE_REQUIRED,
            {
                "reason": "no_active_workspace",
                "intent": intent,
                "text": text,
                "request_id": request_id,
            },
            source=self.name,
        )

    def _publish_legacy_routed(
        self,
        *,
        request_id: str,
        text: str,
        intent: str,
        args: dict[str, Any],
        scope: dict[str, str],
        event: Event,
    ) -> None:
        active_workspace_id = self._resolve_active_workspace_id(event)
        if intent not in _WORKSPACE_OPTIONAL_INTENTS and not active_workspace_id:
            self._defer_no_workspace(request_id, text, intent)
            return

        merged_args = dict(args)
        if scope:
            entity_keys = {k: v for k, v in scope.items() if k.startswith("workspace_entity")}
            if entity_keys:
                merged_args = {**merged_args, **entity_keys}
            if scope.get("workspace_id"):
                merged_args = {**merged_args, "workspace_id": scope["workspace_id"]}

        payload: dict[str, object] = {
            "contract_version": COMMAND_ROUTED_VERSION,
            "request_id": request_id,
            "text": text,
            "intent": intent,
            "args": merged_args,
            "status": "pending",
            "metadata": {"executing": False, "source_router": self.name},
        }
        if scope:
            payload.update(scope)
        self._bus.publish(COMMAND_ROUTED, payload, source=self.name)

    def analyze(
        self,
        text: str,
        *,
        clipboard: object | None = None,
    ) -> ExecutionDecision:
        """Tri-state (+ legacy) classification. Never defaults to chat-as-sink."""
        stripped = text.strip()
        prefix_intent, prefix_args = CommandRouterService.classify(stripped)

        if prefix_intent == INTENT_AGENT:
            spawn_mode = str(prefix_args.get("spawn_mode") or "single")
            capability = {
                "multi": "agent.multi",
                "pipeline": "agent.pipeline",
            }.get(spawn_mode, "agent.run")
            return ExecutionDecision(
                kind=DecisionKind.ACTIONABLE,
                text=stripped,
                capability=capability,
                args=dict(prefix_args),
                reason="agent_capability",
                skip_planner=True,
            )

        if prefix_intent in _LEGACY_INTENTS:
            return ExecutionDecision(
                kind=DecisionKind.LEGACY_ROUTE,
                text=stripped,
                legacy_intent=prefix_intent,
                args=dict(prefix_args),
                reason="legacy_capability_handler",
            )

        if prefix_intent == INTENT_SHELL:
            return ExecutionDecision(
                kind=DecisionKind.ACTIONABLE,
                text=stripped,
                capability="shell",
                args={"command": str(prefix_args.get("command", stripped))},
                reason="shell_command",
                skip_planner=True,
            )

        launch_match = _LAUNCH_RE.match(stripped)
        if launch_match:
            app = launch_match.group(1).lower()
            if app == "calc":
                app = "calculator"
            return ExecutionDecision(
                kind=DecisionKind.ACTIONABLE,
                text=stripped,
                capability="launch_application",
                args={"application": app},
                reason="launch_application",
                skip_planner=True,
            )

        orch_intent, orch_args = self._classifier.classify(stripped)
        if orch_intent is not OrchestrationIntent.UNHANDLED:
            capability = _ORCH_CAPABILITY.get(orch_intent, "")
            if capability:
                return ExecutionDecision(
                    kind=DecisionKind.ACTIONABLE,
                    text=stripped,
                    capability=capability,
                    args=dict(orch_args),
                    reason=orch_intent.value,
                    skip_planner=True,
                )

        if prefix_intent == INTENT_CHAT or orch_intent is OrchestrationIntent.UNHANDLED:
            args: dict[str, Any] = {"prompt": stripped}
            if clipboard:
                args["clipboard"] = str(clipboard)
            lower = stripped.lower()
            if lower.startswith(("open ", "launch ", "start ", "run ", "please ")):
                return ExecutionDecision(
                    kind=DecisionKind.AMBIGUOUS,
                    text=stripped,
                    capability="llm",
                    args=args,
                    reason="ambiguous_actionable_phrasing",
                    skip_planner=True,
                )
            return ExecutionDecision(
                kind=DecisionKind.CONVERSATIONAL,
                text=stripped,
                capability="llm",
                args=args,
                reason="conversational",
                skip_planner=True,
            )

        return ExecutionDecision(
            kind=DecisionKind.AMBIGUOUS,
            text=stripped,
            capability="llm",
            args={"prompt": stripped},
            reason="unclassified",
            skip_planner=True,
        )

    @staticmethod
    def _plan_for_decision(decision: ExecutionDecision) -> ExecutionPlan | None:
        if not decision.capability:
            return None
        if decision.capability.startswith("agent"):
            # Expanded by _dispatch_agent.
            return None
        return ExecutionPlan(
            goal=decision.text,
            steps=(
                PlanStep(
                    step_id="step-1",
                    capability=decision.capability,
                    args=dict(decision.args),
                    require_approval=False,
                ),
            ),
        )
