"""Execution orchestrator — runs approved plans with permission gates (vNext L5).

ADR-018: validates Intentions before TOOL_INVOKE.
ADR-019: publishes execution observations; explicit plan.replan on failure (no ReAct loop).
ADR-021/022: emits DecisionRecord / AutonomyScore updates on escalate paths.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION, build_workspace_context
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    AUTONOMY_SCORE_UPDATED,
    CAPABILITY_COMPLETE,
    CAPABILITY_ERROR,
    CAPABILITY_RUNTIME_REQUEST,
    DECISION_RECORD_UPDATED,
    EXECUTION_OBSERVATION,
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
    ORCHESTRATION_RECEIPT,
    PLAN_REPLAN_REQUEST,
    PLAN_REPLAN_RESULT,
    PLAN_REPLAN_STUCK,
    TOOL_APPROVED,
    TOOL_CONFIRMATION_REQUIRED,
    TOOL_DENIED,
    TOOL_FAILED,
    TOOL_INVOKE,
    TOOL_PARSE_FAILURE,
    TOOL_RESULT,
    TOOL_VALIDATION_FAILURE,
)
from ai_command_center.core.intention_validation import validate_intention
from ai_command_center.core.plan_similarity import is_stuck, serialize_plan
from ai_command_center.domain.autonomy_score import AutonomyScore
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.decision_record import DecisionRecord
from ai_command_center.domain.execution_observation import ExecutionObservation
from ai_command_center.domain.intention import Intention
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.domain.state_context import StateContext
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

_EXTERNAL_PREFIXES = ("mcp.", "external.", "mcp:")
_LLM_CAPABILITIES = frozenset({"llm", "chat"})
_MAX_REPLAN_ATTEMPTS = 2
# Marks orchestrator-built StateContext projections so replan attempts regenerate
# them from the latest observations instead of freezing the first failure summary.
_ORCHESTRATOR_SYNTHESIZED_STATE_CONTEXT = "_orchestrator_synthesized"


def _split_confirmation(payload: dict[str, Any]) -> tuple[str, str]:
    confirmation_id = str(payload.get("confirmation_id") or "").strip()
    run_id = str(payload.get("run_id") or "").strip()
    step_id = str(payload.get("step_id") or "").strip()
    if confirmation_id and ":" in confirmation_id and not run_id:
        run_id, step_id = confirmation_id.split(":", 1)
    return run_id, step_id


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
        # G1 receipt boundary: correlation ids seen on ORCHESTRATION_RECEIPT.
        # EXECUTION_RUN_COMPLETE is SYNC_STANDARD (dispatch_policy.py), so it is
        # dispatched inline — any receipt for a run has been recorded here by the
        # time publish() returns. See _complete_run.
        self._receipted_ids: set[str] = set()

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
        self._unsubscribers.append(
            self._bus.subscribe(PLAN_REPLAN_RESULT, self._on_replan_result)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_APPROVED, self._on_tool_approved)
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_DENIED, self._on_tool_denied)
        )
        self._unsubscribers.append(
            self._bus.subscribe(ORCHESTRATION_RECEIPT, self._on_orchestration_receipt)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._runs.clear()
        self._receipted_ids.clear()

    def _on_orchestration_receipt(self, event: Event) -> None:
        """Record receipt evidence so _complete_run can verify the G1 boundary."""
        request_id = str(event.payload.get("request_id") or "").strip()
        if request_id:
            self._receipted_ids.add(request_id)

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

        known = event.payload.get("known_capabilities")
        known_capabilities: set[str] | None = None
        if isinstance(known, (list, tuple, set)):
            known_capabilities = {str(x) for x in known}

        raw_state = event.payload.get("state_context")
        state_context = dict(raw_state) if isinstance(raw_state, dict) else {}
        raw_receipts = event.payload.get("receipts")
        receipts = (
            [dict(item) for item in raw_receipts if isinstance(item, dict)]
            if isinstance(raw_receipts, list)
            else []
        )

        self._runs[run_id] = {
            "plan": plan,
            "index": 0,
            "workspace_context": workspace_context,
            "state_context": state_context,
            "receipts": receipts,
            "request_id": str(event.payload.get("request_id", "")),
            "correlation": CorrelationContext.from_payload(event.payload).to_payload(),
            "auto_approve": bool(event.payload.get("auto_approve", False)),
            "paused": False,
            "replanning": False,
            "replan_attempts": 0,
            "plan_history": [serialize_plan(plan)],
            "observations": [],
            "known_capabilities": known_capabilities,
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
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if not run.get("paused"):
            return
        step_id = str(event.payload.get("step_id", "")).strip()
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        if step_id and plan.steps[index].step_id != step_id:
            return
        run["paused"] = False
        self._dispatch_step(run_id)

    def _on_tool_result(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if run.get("paused") or run.get("replanning"):
            return
        step_id = str(event.payload.get("step_id", "")).strip()
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        if plan.steps[index].step_id != step_id:
            return
        success = bool(event.payload.get("success", True))
        if not success:
            self._fail_step(
                run_id,
                str(event.payload.get("error") or event.payload.get("message") or "tool failed"),
            )
            return
        facts = event.payload.get("facts")
        self._complete_step(
            run_id,
            output=str(event.payload.get("output", "")),
            facts=dict(facts) if isinstance(facts, dict) else None,
        )

    def _on_tool_failed(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if run.get("paused") or run.get("replanning"):
            return
        step_id = str(event.payload.get("step_id", "")).strip()
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        if step_id and plan.steps[index].step_id != step_id:
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
        if run.get("paused") or run.get("replanning"):
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
        if run.get("paused") or run.get("replanning"):
            return
        step_id = str(event.payload.get("step_id", "")).strip()
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index >= len(plan.steps):
            return
        if plan.steps[index].step_id != step_id:
            return
        self._fail_step(run_id, str(event.payload.get("message") or "capability failed"))

    def _on_replan_result(self, event: Event) -> None:
        run_id = str(event.payload.get("run_id", "")).strip()
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if not run.get("replanning"):
            return
        raw_plan = event.payload.get("plan")
        if not isinstance(raw_plan, dict):
            run["replanning"] = False
            self._fail_run(run_id, "replan result missing plan")
            return
        new_plan = ExecutionPlan.from_dict(raw_plan)
        if not new_plan.steps:
            run["replanning"] = False
            self._fail_run(run_id, "replan produced no steps")
            return

        history = list(run.get("plan_history") or [])
        history.append(serialize_plan(new_plan))
        run["plan_history"] = history
        if is_stuck(history):
            run["replanning"] = False
            self._publish_stuck(run_id, new_plan)
            self._fail_run(run_id, "replan stuck: near-identical plans")
            return

        run["plan"] = new_plan
        run["goal"] = new_plan.goal
        run["index"] = 0
        run["replanning"] = False
        run["paused"] = False
        self._advance_run(run_id)

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
            confirmation_id = f"{run_id}:{step.step_id}"
            self._publish_decision_and_autonomy(
                run_id=run_id,
                step=step,
                summary="awaiting approval",
                hard_policy_block=True,
                policy={"require_approval": True, "security_tier": "gated"},
            )
            self._bus.publish(
                EXECUTION_STEP_AWAITING_APPROVAL,
                {
                    "run_id": run_id,
                    "step_id": step.step_id,
                    "capability": step.capability,
                    "require_approval": True,
                    "confirmation_id": confirmation_id,
                },
                source=self.name,
            )
            # ADR-009 alignment (ADR-018 narrowed): intention confirmation, not tool_call_id
            self._bus.publish(
                TOOL_CONFIRMATION_REQUIRED,
                {
                    "confirmation_id": confirmation_id,
                    "run_id": run_id,
                    "step_id": step.step_id,
                    "capability": step.capability,
                    "args": dict(step.args),
                    "summary": f"Approve capability {step.capability}",
                    "kind": "intention",
                },
                source=self.name,
            )
            return

        self._dispatch_step(run_id)

    def _on_tool_approved(self, event: Event) -> None:
        """ADR-009: UI/tool.approved resumes orchestrator (maps to step approved)."""
        run_id, step_id = _split_confirmation(event.payload)
        if not run_id:
            return
        self._on_step_approved(
            Event(
                topic=EXECUTION_STEP_APPROVED,
                payload={"run_id": run_id, "step_id": step_id},
                source=event.source,
            )
        )

    def _on_tool_denied(self, event: Event) -> None:
        """ADR-009: denied confirmation fails the step (no LLM tool-loop SoT)."""
        run_id, step_id = _split_confirmation(event.payload)
        if not run_id or run_id not in self._runs:
            return
        run = self._runs[run_id]
        if not run.get("paused"):
            return
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        if index < len(plan.steps) and step_id and plan.steps[index].step_id != step_id:
            return
        run["paused"] = False
        reason = str(event.payload.get("reason") or "confirmation denied")
        self._fail_step(run_id, reason, allow_replan=True)

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

        intention = Intention.from_plan_step(step)
        validation = validate_intention(
            intention,
            known_capabilities=run.get("known_capabilities"),
        )
        if not validation.ok:
            topic = (
                TOOL_PARSE_FAILURE
                if validation.kind == "parse"
                else TOOL_VALIDATION_FAILURE
            )
            self._bus.publish(
                topic,
                {
                    "run_id": run_id,
                    "step_id": step.step_id,
                    "capability": step.capability,
                    "kind": validation.kind,
                    "message": validation.message,
                    "intention": intention.to_dict(),
                },
                source=self.name,
            )
            self._fail_step(
                run_id,
                f"intention {validation.kind} failure: {validation.message}",
                allow_replan=False,
            )
            return

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
        tool_args = {
            k: v
            for k, v in dict(step.args).items()
            if k not in {"actor_type", "workflow_run_id", "workflow_id"}
        }
        if workspace_context.get("workspace_id") and "workspace_id" not in tool_args:
            tool_args["workspace_id"] = workspace_context["workspace_id"]
        if workspace_context.get("entity_id") and "entity_id" not in tool_args:
            tool_args["entity_id"] = workspace_context["entity_id"]
        self._bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": invoke_id,
                "tool": step.capability,
                "args": tool_args,
                "run_id": run_id,
                "step_id": step.step_id,
                "actor_type": actor_type,
                "workspace_context": workspace_context,
                "intention": intention.to_dict(),
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

    def _publish_observation(
        self,
        run_id: str,
        *,
        success: bool,
        output: str = "",
        error: str = "",
    ) -> ExecutionObservation:
        run = self._runs[run_id]
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        step = plan.steps[index]
        obs = ExecutionObservation(
            run_id=run_id,
            step_id=step.step_id,
            step_index=index,
            capability=step.capability,
            args=dict(step.args),
            success=success,
            output=output,
            error=error,
        )
        observations = list(run.get("observations") or [])
        observations.append(obs.to_dict())
        run["observations"] = observations
        self._bus.publish(EXECUTION_OBSERVATION, obs.to_dict(), source=self.name)
        return obs

    def _publish_decision_and_autonomy(
        self,
        *,
        run_id: str,
        step: PlanStep,
        summary: str,
        hard_policy_block: bool,
        policy: dict[str, Any],
        evidence: dict[str, Any] | None = None,
        receipt: dict[str, Any] | None = None,
        verification: dict[str, Any] | None = None,
    ) -> None:
        run = self._runs.get(run_id) or {}
        record = DecisionRecord(
            record_id=uuid.uuid4().hex,
            run_id=run_id,
            step_id=step.step_id,
            capability=step.capability,
            evidence=dict(evidence or {"observations": list(run.get("observations") or [])}),
            policy=dict(policy),
            receipt=dict(receipt or {}),
            verification=dict(verification or {}),
            summary=summary,
        )
        self._bus.publish(DECISION_RECORD_UPDATED, record.to_dict(), source=self.name)
        score = AutonomyScore.compute(
            policy_confidence=0.2 if hard_policy_block else 0.9,
            evidence_confidence=0.7 if run.get("observations") else 0.4,
            verification_confidence=0.5,
            execution_confidence=0.5,
            hard_policy_block=hard_policy_block,
            reason=summary,
        )
        self._bus.publish(
            AUTONOMY_SCORE_UPDATED,
            {**score.to_dict(), "run_id": run_id, "step_id": step.step_id},
            source=self.name,
        )

    def _publish_stuck(self, run_id: str, plan: ExecutionPlan) -> None:
        run = self._runs[run_id]
        self._bus.publish(
            PLAN_REPLAN_STUCK,
            {
                "run_id": run_id,
                "request_id": run.get("request_id", ""),
                "goal": plan.goal,
                "plan": plan.to_dict(),
                "plan_history": list(run.get("plan_history") or []),
                "observations": list(run.get("observations") or []),
                "correlation": dict(run.get("correlation") or {}),
            },
            source=self.name,
        )
        if plan.steps:
            self._publish_decision_and_autonomy(
                run_id=run_id,
                step=plan.steps[0],
                summary="replan stuck — escalate to human",
                hard_policy_block=True,
                policy={"stuck": True, "require_approval": True},
            )

    def _resolve_run_state_context(self, run: dict[str, Any]) -> dict[str, Any]:
        """Prefer caller-supplied StateContext; else synthesize a fresh WM projection.

        Caller-provided projections are preserved across replan attempts. Projections
        synthesized by this orchestrator are tagged and recomputed each time so the
        replan summary includes observations recorded since the previous attempt.
        """
        raw = run.get("state_context")
        if (
            isinstance(raw, dict)
            and not raw.get(_ORCHESTRATOR_SYNTHESIZED_STATE_CONTEXT)
            and (
                raw.get("summary")
                or raw.get("entities")
                or raw.get("memories")
                or raw.get("goals")
            )
        ):
            return dict(raw)
        workspace_context = dict(run.get("workspace_context") or {})
        workspace_id = str(workspace_context.get("workspace_id") or "")
        if isinstance(raw, dict) and raw.get("workspace_id"):
            workspace_id = str(raw.get("workspace_id") or workspace_id)
        obs_lines: list[str] = []
        for item in list(run.get("observations") or [])[-8:]:
            if not isinstance(item, dict):
                continue
            obs_lines.append(
                f"step={item.get('step_id')} cap={item.get('capability')} "
                f"ok={item.get('success')} err={item.get('error', '')}"
            )
        summary = "; ".join(obs_lines) if obs_lines else ""
        plan = run.get("plan")
        goal = str(run.get("goal") or (getattr(plan, "goal", "") if plan else ""))
        payload = StateContext(
            workspace_id=workspace_id,
            summary=summary,
            query_text=goal,
        ).to_dict()
        payload[_ORCHESTRATOR_SYNTHESIZED_STATE_CONTEXT] = True
        return payload

    def _build_wm_snapshot(self, run_id: str, error: str) -> dict[str, Any]:
        """Structured WM / execution snapshot for plan.replan.request (ADR-019)."""
        run = self._runs[run_id]
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        step = plan.steps[index] if 0 <= index < len(plan.steps) else None
        state_context = self._resolve_run_state_context(run)
        failed_step: dict[str, Any] = {
            "index": index,
            "error": error,
        }
        if step is not None:
            failed_step.update(
                {
                    "step_id": step.step_id,
                    "capability": step.capability,
                    "args": dict(step.args),
                }
            )
        return {
            "workspace_id": state_context.get("workspace_id", ""),
            "state_context": state_context,
            "observations": list(run.get("observations") or []),
            "step_outputs": list(run.get("step_outputs") or []),
            "plan_history": list(run.get("plan_history") or []),
            "receipts": list(run.get("receipts") or []),
            "failed_step": failed_step,
        }

    def _request_replan(self, run_id: str, error: str) -> bool:
        """Publish explicit replan request. Returns True if replan requested."""
        run = self._runs[run_id]
        attempts = int(run.get("replan_attempts") or 0)
        if attempts >= _MAX_REPLAN_ATTEMPTS:
            return False
        plan: ExecutionPlan = run["plan"]
        run["replan_attempts"] = attempts + 1
        run["replanning"] = True
        wm_snapshot = self._build_wm_snapshot(run_id, error)
        state_context = dict(wm_snapshot.get("state_context") or {})
        # Keep run projection fresh for subsequent attempts / stuck escalate.
        run["state_context"] = state_context
        self._bus.publish(
            PLAN_REPLAN_REQUEST,
            {
                "run_id": run_id,
                "request_id": run.get("request_id", ""),
                "goal": plan.goal,
                "error": error,
                "failed_index": int(run["index"]),
                "plan": plan.to_dict(),
                "observations": list(run.get("observations") or []),
                "step_outputs": list(run.get("step_outputs") or []),
                "plan_history": list(run.get("plan_history") or []),
                "receipts": list(run.get("receipts") or []),
                "state_context": state_context,
                "wm_snapshot": wm_snapshot,
                "workspace_context": dict(run.get("workspace_context") or {}),
                "correlation": dict(run.get("correlation") or {}),
                "replan_attempt": run["replan_attempts"],
            },
            source=self.name,
        )
        return True

    def _complete_step(
        self,
        run_id: str,
        *,
        output: str = "",
        facts: dict[str, Any] | None = None,
    ) -> None:
        if run_id not in self._runs:
            return
        run = self._runs[run_id]
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        step = plan.steps[index]
        self._publish_observation(run_id, success=True, output=output)
        outputs = list(run.get("step_outputs") or [])
        step_record: dict[str, Any] = {
            "step_id": step.step_id,
            "capability": step.capability,
            "output": output,
            "success": True,
        }
        if facts:
            step_record["facts"] = dict(facts)
        outputs.append(step_record)
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

    def _fail_step(self, run_id: str, error: str, *, allow_replan: bool = True) -> None:
        if run_id not in self._runs:
            return
        run = self._runs[run_id]
        plan: ExecutionPlan = run["plan"]
        index = int(run["index"])
        step = plan.steps[index]
        self._publish_observation(run_id, success=False, error=error)
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
        if allow_replan and self._request_replan(run_id, error):
            # EventBus is sync: if PlannerService handled the replan, replanning is cleared.
            # If still set, no handler answered — fail the run instead of hanging.
            current = self._runs.get(run_id)
            if current is not None and current.get("replanning"):
                current["replanning"] = False
                self._fail_run(run_id, error)
            return
        self._fail_run(run_id, error)

    def _complete_run(self, run_id: str) -> None:
        run = self._runs.pop(run_id, None)
        request_id = str(run.get("request_id", "")) if run else ""
        correlation = dict(run.get("correlation") or {}) if run else {}
        plan = run.get("plan") if run else None
        step_outputs = list(run.get("step_outputs") or []) if run else []
        observations = list(run.get("observations") or []) if run else []
        plan_dict = plan.to_dict() if isinstance(plan, ExecutionPlan) else {}
        workspace_context = dict(run.get("workspace_context") or {}) if run else {}
        goal = (
            getattr(plan, "goal", "")
            if plan
            else str(run.get("goal", "") if run else "")
        )

        # Correlation ids a receipt for this run may legitimately carry.
        # OrchestrationService keys receipts on request_id, falling back to run_id.
        correlating_ids = {i for i in (request_id, run_id) if i}
        self._receipted_ids -= correlating_ids

        self._bus.publish(
            EXECUTION_RUN_COMPLETE,
            {
                "run_id": run_id,
                "request_id": request_id,
                "correlation": correlation,
                "goal": goal,
                "success": True,
                "step_outputs": step_outputs,
                "observations": observations,
                "plan": plan_dict,
                "workspace_context": workspace_context,
            },
            source=self.name,
        )

        # G1 receipt boundary — fail closed.
        # EXECUTION_RUN_COMPLETE dispatches inline, so a conforming receipt observer
        # has already run. If no ExecutionReceipt was produced for this run, the
        # side effect happened but is unverified: report failure, never success.
        # Read once, then clear unconditionally: ids are caller-supplied and may be
        # reused across runs, so a leftover entry must never satisfy a later guard.
        receipted = bool(self._receipted_ids & correlating_ids)
        self._receipted_ids -= correlating_ids
        if not receipted:
            _logger.error(
                "execution.receipt_boundary_violation run_id=%s request_id=%s — "
                "run completed without an ExecutionReceipt; failing closed",
                run_id,
                request_id,
            )
            self._bus.publish(
                EXECUTION_RUN_FAILED,
                {
                    "run_id": run_id,
                    "request_id": request_id,
                    "error": (
                        "receipt boundary violation: execution completed without an "
                        "ExecutionReceipt or TruthBoundary validation"
                    ),
                    "receipt_boundary_violation": True,
                    "correlation": correlation,
                    "goal": goal,
                    "success": False,
                    "step_outputs": step_outputs,
                    "observations": observations,
                    "plan": plan_dict,
                    "workspace_context": workspace_context,
                },
                source=self.name,
            )
            self._receipted_ids -= correlating_ids
            return

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
                "observations": list(run.get("observations") or []) if run else [],
                "plan": plan.to_dict() if isinstance(plan, ExecutionPlan) else {},
                "workspace_context": dict(run.get("workspace_context") or {}) if run else {},
            },
            source=self.name,
        )
        # Clear after publishing: the failure itself is receipted, and that entry
        # must not accumulate or satisfy a later run reusing the same ids.
        self._receipted_ids -= {i for i in (request_id, run_id) if i}
