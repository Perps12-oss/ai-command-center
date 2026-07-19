"""Single Execution Authority — sole creator of executable work.

Every typed UI_COMMAND becomes an ExecutionPlan.
StateAuthority projects World Model context before planning/dispatch.
Never publishes TOOL_INVOKE or LLM_REQUEST.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable
from typing import Any

from ai_command_center.core.command_classify import classify_command
from ai_command_center.core.contracts import COMMAND_DEFERRED_VERSION, build_workspace_context
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.intents import (
    INTENT_AGENT,
    INTENT_CHAT,
    INTENT_SHELL,
)
from ai_command_center.core.events.topics import (
    AGENT_EXECUTION_REQUEST,
    AGENT_SPAWN_REQUEST,
    COMMAND_DEFERRED,
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
from ai_command_center.domain.state_context import StateContext
from ai_command_center.orchestration.intents.classifier import RuleBasedIntentClassifier
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.services.agent_runtime_service import AgentRuntimeService
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

_LAUNCH_RE = re.compile(
    r"^\s*(?:open|launch|start)\s+(\w+)\s*$",
    re.IGNORECASE,
)

_GOAL_RE = re.compile(
    r"^\s*(?:prepare(?:\s+for)?|plan(?:\s+for)?|get\s+ready\s+for|organize|set\s+up)\b",
    re.IGNORECASE,
)

_MEMORY_RECALL_RE = re.compile(
    r"^\s*(?:what\s+is\s+my|what's\s+my|whats\s+my|do\s+you\s+remember|"
    r"recall\s+my|favourite|favorite)\b",
    re.IGNORECASE,
)

_FIND_NOTE_RE = re.compile(
    r"^\s*(?:find|search)\s+(?:notes?\s+)?(.+)$",
    re.IGNORECASE,
)

# Capabilities that may proceed without an active workspace.
_WORKSPACE_OPTIONAL_CAPABILITIES: frozenset[str] = frozenset({"navigate"})

_ORCH_CAPABILITY: dict[OrchestrationIntent, str] = {
    OrchestrationIntent.LAUNCH_APPLICATION: "launch_application",
    OrchestrationIntent.EXECUTE_SHELL: "shell",
    OrchestrationIntent.SYSTEM_TIME_QUERY: "system_time_query",
    OrchestrationIntent.CALENDAR_QUERY: "calendar_query",
    OrchestrationIntent.CALENDAR_EVENT_CREATE: "calendar_event_create",
}

_PREFIX_CAPABILITY: dict[str, str] = {
    "navigate": "navigate",
    "note_search": "notes.search",
    "note_new": "notes.create",
    "memory_remember": "memory.store",
    "memory_select": "memory.query",
}


class ExecutionAuthorityService(BaseService):
    """Owns intake. Emits GOAL_SUBMIT_REQUEST only — never TOOL_INVOKE."""

    name = "execution_authority"

    def __init__(
        self,
        bus,
        *,
        classifier: RuleBasedIntentClassifier | None = None,
        agent_runtime: AgentRuntimeService | None = None,
        state_authority: Any | None = None,
    ) -> None:
        super().__init__(bus)
        self._classifier = classifier or RuleBasedIntentClassifier()
        self._agent_runtime = agent_runtime
        self._state_authority = state_authority
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

    def _project_state(self, text: str, workspace_id: str) -> StateContext:
        if self._state_authority is None:
            return StateContext.empty(workspace_id=workspace_id, query_text=text)
        return self._state_authority.project(text=text, workspace_id=workspace_id)

    def _on_ui_command(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return

        request_id = uuid.uuid4().hex
        scope = self._workspace_scope(event)
        clipboard = event.payload.get("clipboard")
        state_context = self._project_state(text, scope.get("workspace_id", ""))
        decision = self.analyze(text, clipboard=clipboard, state_context=state_context)

        self._bus.publish(
            EXECUTION_AUTHORITY_DECISION,
            {
                "request_id": request_id,
                **decision.to_payload(),
                **scope,
                "state_context": state_context.to_dict(),
            },
            source=self.name,
        )

        active_workspace_id = self._resolve_active_workspace_id(event)
        if (
            not active_workspace_id
            and decision.capability not in _WORKSPACE_OPTIONAL_CAPABILITIES
        ):
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
                state_context=state_context,
            )
            return

        if decision.capability == "goal":
            # Free-text goals go through planner with World Model context.
            self._submit_plan(
                request_id=request_id,
                text=text,
                decision=decision,
                plan=None,
                scope=scope,
                state_context=state_context,
                skip_planner=False,
            )
            return

        plan = self._plan_for_decision(decision)
        if decision.capability == "llm" and state_context.summary:
            # Inject state into conversational args for ChatHandler.
            args = dict(decision.args)
            snippets = state_context.to_planner_snippets()
            if snippets:
                args["state_context_snippets"] = snippets
                decision = ExecutionDecision(
                    kind=decision.kind,
                    text=decision.text,
                    capability=decision.capability,
                    args=args,
                    reason=decision.reason,
                    skip_planner=decision.skip_planner,
                )
                plan = self._plan_for_decision(decision)
        self._submit_plan(
            request_id=request_id,
            text=text,
            decision=decision,
            plan=plan,
            scope=scope,
            state_context=state_context,
        )

    def _on_workflow_execution_request(self, event: Event) -> None:
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
        ws = str(workspace_context.get("workspace_id") or "")
        state_context = self._project_state(f"workflow:{workflow_id}", ws)

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
        decision = ExecutionDecision(
            kind=DecisionKind.ACTIONABLE,
            text=plan.goal,
            capability="workflow",
            reason="workflow_start",
            skip_planner=True,
        )
        self._submit_plan(
            request_id=run_id,
            text=plan.goal,
            decision=decision,
            plan=plan,
            scope={"workspace_id": ws} if ws else {},
            state_context=state_context,
            workspace_context_override=workspace_context,
            extra_payload={"workflow_run_id": run_id, "workflow_id": workflow_id},
        )

    def _on_agent_execution_request(self, event: Event) -> None:
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
        ws = str(event.payload.get("workspace_id") or "")
        state_context = self._project_state(task or plan.goal, ws)
        decision = ExecutionDecision(
            kind=DecisionKind.ACTIONABLE,
            text=plan.goal,
            capability="agent.shell",
            reason="agent_execution_request",
            skip_planner=True,
        )
        self._submit_plan(
            request_id=request_id,
            text=plan.goal,
            decision=decision,
            plan=plan,
            scope={"workspace_id": ws} if ws else {},
            state_context=state_context,
        )

    def _dispatch_agent(
        self,
        *,
        request_id: str,
        text: str,
        decision: ExecutionDecision,
        scope: dict[str, str],
        state_context: StateContext,
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
        runtime = self._agent_runtime
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
            state_context=state_context,
        )

    def _submit_plan(
        self,
        *,
        request_id: str,
        text: str,
        decision: ExecutionDecision,
        plan: ExecutionPlan | None,
        scope: dict[str, str],
        state_context: StateContext,
        skip_planner: bool | None = None,
        workspace_context_override: dict[str, Any] | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> None:
        use_synthetic = decision.skip_planner if skip_planner is None else skip_planner
        correlation = CorrelationContext.new(goal_id=request_id).to_payload()
        correlation["correlation_id"] = request_id

        if workspace_context_override is not None:
            workspace_context = dict(workspace_context_override)
        else:
            workspace_context = build_workspace_context(
                workspace_id=scope.get("workspace_id"),
                entity_id=scope.get("workspace_entity_id")
                or scope.get("selected_entity_id"),
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
            "state_context": state_context.to_dict(),
        }
        if plan is not None and use_synthetic:
            payload["plan"] = plan.to_dict()
            payload["planner_mode"] = "synthetic"
        elif not use_synthetic:
            # Planner path — pass World Model snippets as workspace hints.
            payload["workspace_snippets"] = state_context.to_planner_snippets()
            payload["planner_mode"] = "state_aware"
        if extra_payload:
            payload.update(extra_payload)

        _logger.info(
            "execution_authority.dispatch request_id=%s kind=%s capability=%s "
            "skip_planner=%s state_entities=%d",
            request_id,
            decision.kind.value,
            decision.capability,
            use_synthetic,
            len(state_context.entities),
        )
        self._bus.publish(GOAL_SUBMIT_REQUEST, payload, source=self.name)

    def _defer_no_workspace(self, request_id: str, text: str, intent: str) -> None:
        deferred_payload = {
            "contract_version": COMMAND_DEFERRED_VERSION,
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

    def analyze(
        self,
        text: str,
        *,
        clipboard: object | None = None,
        state_context: StateContext | None = None,
    ) -> ExecutionDecision:
        """Classify into ACTIONABLE / CONVERSATIONAL / AMBIGUOUS. No legacy routes."""
        stripped = text.strip()
        ctx = state_context or StateContext.empty(query_text=stripped)
        prefix_intent, prefix_args = classify_command(stripped)

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

        # Former legacy prefixes → first-class capabilities.
        if prefix_intent in _PREFIX_CAPABILITY:
            capability = _PREFIX_CAPABILITY[prefix_intent]
            args = dict(prefix_args)
            if capability == "notes.create":
                args.setdefault("body", args.get("body") or stripped)
            if capability == "notes.search":
                args.setdefault("query", args.get("query") or stripped)
            if capability == "memory.store":
                args.setdefault("body", args.get("body") or stripped)
            if capability == "memory.query":
                args.setdefault("query", args.get("query") or stripped)
            return ExecutionDecision(
                kind=DecisionKind.ACTIONABLE,
                text=stripped,
                capability=capability,
                args=args,
                reason="state_capability",
                skip_planner=True,
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

        # Goal phrasing → planner with state context.
        if _GOAL_RE.match(stripped):
            return ExecutionDecision(
                kind=DecisionKind.ACTIONABLE,
                text=stripped,
                capability="goal",
                args={"goal": stripped},
                reason="goal_phrasing",
                skip_planner=False,
            )

        # Memory recall from natural language — prefer stored state over LLM.
        if _MEMORY_RECALL_RE.match(stripped) or any(
            m.get("label", "").lower() in stripped.lower() for m in ctx.memories
        ):
            return ExecutionDecision(
                kind=DecisionKind.ACTIONABLE,
                text=stripped,
                capability="memory.query",
                args={"query": stripped},
                reason="memory_recall",
                skip_planner=True,
            )

        find_match = _FIND_NOTE_RE.match(stripped)
        if find_match:
            return ExecutionDecision(
                kind=DecisionKind.ACTIONABLE,
                text=stripped,
                capability="notes.search",
                args={"query": find_match.group(1).strip()},
                reason="note_search_phrasing",
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
        if not decision.capability or decision.capability in {"goal"}:
            return None
        if decision.capability.startswith("agent") and decision.capability not in {
            "agent.shell",
        }:
            # Expanded by _dispatch_agent.
            if decision.capability in {"agent.run", "agent.multi", "agent.pipeline"}:
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
