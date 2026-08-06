"""Planner layer — converts goals into execution manifests without executing."""

from __future__ import annotations

import re
import json
import uuid
from collections.abc import Callable
from typing import Any

from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CAPABILITY_CATALOG_REQUEST,
    CAPABILITY_CATALOG_RESULT,
    PLAN_FAILED,
    PLAN_GENERATED,
    PLAN_REPLAN_REQUEST,
    PLAN_REPLAN_RESULT,
    PLAN_REQUEST,
    WORKSPACE_CONTEXT_REQUEST,
    WORKSPACE_CONTEXT_RESULT,
)
from ai_command_center.core.wm_first_context import (
    build_wm_first_context,
    build_wm_first_snippets,
)
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
from ai_command_center.domain.state_authority import StateQuery
from ai_command_center.domain.state_context import StateContext
from ai_command_center.services.base import BaseService

_NOTE_GOAL = re.compile(r"\b(note|memo)\b", re.IGNORECASE)
_NOTE_ACTION = re.compile(r"\b(create|add|new|write)\b", re.IGNORECASE)
_TASK_GOAL = re.compile(r"\b(task|shopping|todo|list)\b", re.IGNORECASE)


def _spec_lookup(specs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(spec["name"]): spec for spec in specs if spec.get("name")}


def _pick_capability(
    specs: list[dict[str, Any]],
    *,
    preferred: tuple[str, ...],
    fallback: str = "",
) -> tuple[str, bool]:
    """Return capability name and require_approval from catalog specs."""
    by_name = _spec_lookup(specs)
    for name in preferred:
        if name in by_name:
            spec = by_name[name]
            return name, bool(spec.get("requires_approval", False))
    if fallback and fallback in by_name:
        spec = by_name[fallback]
        return fallback, bool(spec.get("requires_approval", False))
    if specs:
        first = specs[0]
        return str(first["name"]), bool(first.get("requires_approval", False))
    return "", False


def build_deterministic_plan(goal: str, specs: list[dict[str, Any]]) -> ExecutionPlan:
    """Rule-based planner skeleton — LLM JSON parsing is Phase C follow-up."""
    goal_text = goal.strip()
    if not goal_text:
        return ExecutionPlan(goal="", steps=())

    launch_match = re.match(
        r"^\s*(?:open|launch|start)\s+(\w+)\s*$",
        goal_text,
        re.IGNORECASE,
    )
    if launch_match:
        app = launch_match.group(1).lower()
        if app == "calc":
            app = "calculator"
        return ExecutionPlan(
            goal=goal_text,
            steps=(
                PlanStep(
                    step_id="step-1",
                    capability="launch_application",
                    args={"application": app},
                    require_approval=False,
                ),
            ),
        )

    if goal_text.startswith(">") or re.match(
        r"^\s*(echo |dir\b|cd |ls |pwd\b|whoami\b)",
        goal_text,
        re.IGNORECASE,
    ):
        command = goal_text[1:].strip() if goal_text.startswith(">") else goal_text
        return ExecutionPlan(
            goal=goal_text,
            steps=(
                PlanStep(
                    step_id="step-1",
                    capability="shell",
                    args={"command": command},
                    require_approval=False,
                ),
            ),
        )

    if _NOTE_GOAL.search(goal_text) and _NOTE_ACTION.search(goal_text):
        title_match = re.search(
            r"(?:called|named|titled)\s+[\"']?([^\"']+)[\"']?",
            goal_text,
            re.IGNORECASE,
        )
        title = title_match.group(1).strip() if title_match else goal_text[:120]
        capability, require_approval = _pick_capability(
            specs,
            preferred=("create_note", "note.create"),
        )
        if capability:
            return ExecutionPlan(
                goal=goal_text,
                steps=(
                    PlanStep(
                        step_id="step-1",
                        capability=capability,
                        args={"title": title},
                        require_approval=require_approval,
                    ),
                ),
            )

    if _TASK_GOAL.search(goal_text):
        capability, require_approval = _pick_capability(
            specs,
            preferred=("create_task", "create_entity", "create_note"),
        )
        if capability:
            return ExecutionPlan(
                goal=goal_text,
                steps=(
                    PlanStep(
                        step_id="step-1",
                        capability=capability,
                        args={"title": goal_text[:120]},
                        require_approval=require_approval,
                    ),
                ),
            )

    capability, require_approval = _pick_capability(
        specs,
        preferred=("search_files", "create_note"),
    )
    if not capability:
        return ExecutionPlan(goal=goal_text, steps=())

    return ExecutionPlan(
        goal=goal_text,
        steps=(
            PlanStep(
                step_id="step-1",
                capability=capability,
                args={"query": goal_text},
                require_approval=require_approval,
            ),
        ),
    )


def parse_structured_plan_response(raw_response: str) -> ExecutionPlan:
    """Parse a planner LLM JSON response into a safe execution manifest."""
    text = raw_response.strip()
    if not text:
        return ExecutionPlan(goal="", steps=())
    if text.startswith("```"):
        text = text.strip("`")
        first_newline = text.find("\n")
        if first_newline >= 0 and not text[:first_newline].strip().startswith("{"):
            text = text[first_newline:].strip()
        elif text.lower().startswith("json"):
            text = text[4:].strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("planner response must be a JSON object")
    confidence = float(data.get("confidence", 0.0) or 0.0)
    if confidence < 0.1:
        return ExecutionPlan(goal=str(data.get("goal", "")), steps=())
    action = data.get("action")
    if isinstance(action, dict) and "steps" not in data:
        data["steps"] = [action]
    return ExecutionPlan.from_dict(data)


class PlannerService(BaseService):
    """Subscribes to plan.request and publishes plan.generated — never executes.

    Contract R2: every plan consumes a State Authority projection (payload or
    live ``query``). Chat / ContextManager alone is never the sole workspace truth.
    """

    name = "planner"

    def __init__(
        self,
        bus,
        *,
        context_manager: ContextManager,
        state_authority: Any | None = None,
    ) -> None:
        super().__init__(bus)
        self._context_manager = context_manager
        self._state_authority = state_authority
        self._unsubscribers: list[Callable[[], None]] = []

    def _resolve_state_context(
        self,
        *,
        goal: str,
        workspace_id: str,
        payload: dict[str, Any],
    ) -> StateContext:
        """Require a StateProjection on every PLAN_REQUEST (contract R2)."""
        raw = payload.get("state_context")
        if isinstance(raw, dict):
            ctx = StateContext.from_dict(raw)
            if ctx.summary or ctx.entities or ctx.memories or ctx.goals:
                return ctx
        if self._state_authority is not None:
            return self._state_authority.query(
                StateQuery(workspace_id=workspace_id, text=goal),
            )
        if isinstance(raw, dict):
            return StateContext.from_dict(raw)
        return StateContext.empty(workspace_id=workspace_id, query_text=goal)

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(PLAN_REQUEST, self._on_plan_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(PLAN_REPLAN_REQUEST, self._on_replan_request)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _fetch_workspace_snippets(
        self,
        request_id: str,
        *,
        workspace_id: str,
        entity_id: str = "",
    ) -> list[str]:
        snippets: list[str] = []

        def on_result(event: Event) -> None:
            if str(event.payload.get("request_id", "")) == request_id:
                raw = event.payload.get("snippets") or []
                snippets.extend(str(item) for item in raw if str(item).strip())

        unsub = self._bus.subscribe(WORKSPACE_CONTEXT_RESULT, on_result)
        try:
            payload: dict[str, object] = {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "max_depth": 2,
            }
            if entity_id:
                payload["entity_id"] = entity_id
            self._bus.publish(WORKSPACE_CONTEXT_REQUEST, payload, source=self.name)
        finally:
            unsub()
        return snippets

    def _fetch_capability_specs(
        self,
        request_id: str,
        entity_types: list[str],
    ) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []

        def on_result(event: Event) -> None:
            if str(event.payload.get("request_id", "")) == request_id:
                raw = event.payload.get("specs") or []
                specs.extend(dict(item) for item in raw if isinstance(item, dict))

        unsub = self._bus.subscribe(CAPABILITY_CATALOG_RESULT, on_result)
        try:
            self._bus.publish(
                CAPABILITY_CATALOG_REQUEST,
                {"request_id": request_id, "entity_types": entity_types},
                source=self.name,
            )
        finally:
            unsub()
        return specs

    def _on_plan_request(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or uuid.uuid4())
        goal = str(event.payload.get("goal", "")).strip()
        goal_id = str(event.payload.get("goal_id") or "")
        correlation = CorrelationContext.from_payload(event.payload)
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        entity_id = str(
            event.payload.get("entity_id")
            or event.payload.get("selected_entity_id", "")
        ).strip()
        entity_type = str(
            event.payload.get("entity_type")
            or event.payload.get("selected_entity_type", "")
        ).strip()
        entity_types_raw = event.payload.get("entity_types") or []
        entity_types = [str(item) for item in entity_types_raw if str(item).strip()]
        if entity_type and entity_type not in entity_types:
            entity_types.append(entity_type)
        if not entity_types:
            entity_types = ["task", "note", "card"]

        if not goal:
            self._bus.publish(
                PLAN_FAILED,
                {
                    "request_id": request_id,
                    "goal": goal,
                    "goal_id": goal_id,
                    "error": "goal is required",
                    "correlation": correlation.to_payload(),
                },
                source=self.name,
            )
            return

        try:
            state_context = self._resolve_state_context(
                goal=goal,
                workspace_id=workspace_id,
                payload=dict(event.payload or {}),
            )
            workspace_snippets: list[str] = []
            # Contract path: State Authority projection first.
            workspace_snippets.extend(state_context.to_planner_snippets())
            injected = event.payload.get("workspace_snippets")
            if isinstance(injected, list):
                workspace_snippets.extend(
                    str(item) for item in injected if str(item).strip()
                )
            if workspace_id:
                workspace_snippets.extend(
                    self._fetch_workspace_snippets(
                        request_id,
                        workspace_id=workspace_id,
                        entity_id=entity_id,
                    )
                )
            # Deduplicate while preserving order.
            seen: set[str] = set()
            deduped: list[str] = []
            for snippet in workspace_snippets:
                if snippet not in seen:
                    seen.add(snippet)
                    deduped.append(snippet)
            workspace_snippets = deduped

            specs = self._fetch_capability_specs(request_id, entity_types)

            # ADR-020 M2: WM / state snippets first; ContextManager is budget-only.
            workspace_snippets = build_wm_first_snippets(
                state_context=state_context,
                extra=workspace_snippets,
            )
            bundle = self._context_manager.build_context(
                goal,
                workspace_snippets=workspace_snippets or None,
            )

            raw_plan_response = str(
                event.payload.get("planner_response")
                or event.payload.get("llm_plan_response")
                or ""
            )
            if raw_plan_response:
                plan = parse_structured_plan_response(raw_plan_response)
                planner_mode = "llm_structured"
            else:
                plan = build_deterministic_plan(goal, specs)
                planner_mode = "deterministic"
            if state_context.summary or state_context.entities:
                planner_mode = f"{planner_mode}+state_aware"
            if not plan.steps:
                self._bus.publish(
                    PLAN_FAILED,
                    {
                        "request_id": request_id,
                        "goal": goal,
                        "goal_id": goal_id,
                        "error": "no capabilities available for goal",
                        "correlation": correlation.to_payload(),
                    },
                    source=self.name,
                )
                return

            self._bus.publish(
                PLAN_GENERATED,
                {
                    "request_id": request_id,
                    "goal": goal,
                    "goal_id": goal_id,
                    "plan": plan.to_dict(),
                    "planner_mode": planner_mode,
                    "context_version": bundle.version,
                    "context_token_estimate": bundle.token_estimate,
                    "state_context": state_context.to_dict(),
                    "correlation": correlation.to_payload(),
                },
                source=self.name,
            )
        except Exception as exc:
            self._bus.publish(
                PLAN_FAILED,
                {
                    "request_id": request_id,
                    "goal": goal,
                    "goal_id": goal_id,
                    "error": str(exc),
                    "correlation": correlation.to_payload(),
                },
                source=self.name,
            )

    def _on_replan_request(self, event: Event) -> None:
        """Explicit replan (ADR-019): revise plan from observations — no orchestrator ReAct."""
        run_id = str(event.payload.get("run_id", "")).strip()
        request_id = str(event.payload.get("request_id") or uuid.uuid4().hex)
        goal = str(event.payload.get("goal", "")).strip()
        error = str(event.payload.get("error", "")).strip()
        observations = event.payload.get("observations") or []
        correlation = CorrelationContext.from_payload(event.payload)
        workspace_context = event.payload.get("workspace_context")
        workspace_id = ""
        if isinstance(workspace_context, dict):
            workspace_id = str(workspace_context.get("workspace_id", "")).strip()

        if not goal:
            self._bus.publish(
                PLAN_REPLAN_RESULT,
                {
                    "run_id": run_id,
                    "request_id": request_id,
                    "error": "goal is required for replan",
                    "correlation": correlation.to_payload(),
                },
                source=self.name,
            )
            return

        obs_snippets: list[str] = [
            f"Replan after failure: {error}" if error else "Replan requested"
        ]
        if isinstance(observations, list):
            for item in observations[-8:]:
                if isinstance(item, dict):
                    obs_snippets.append(
                        f"obs step={item.get('step_id')} cap={item.get('capability')} "
                        f"ok={item.get('success')} err={item.get('error', '')}"
                    )

        try:
            specs = self._fetch_capability_specs(request_id, ["task", "note", "card"])
            state_context = self._resolve_state_context(
                goal=goal,
                workspace_id=workspace_id,
                payload=dict(event.payload or {}),
            )
            wm_snippets = build_wm_first_snippets(
                state_context=state_context,
                observations=observations if isinstance(observations, list) else (),
                extra=obs_snippets,
            )
            bundle = build_wm_first_context(
                self._context_manager,
                goal,
                state_context=state_context,
                observations=observations if isinstance(observations, list) else (),
                extra_snippets=obs_snippets,
            )
            # Prefer injected planner_response for tests / future LLM assist via Planner only.
            raw_plan_response = str(
                event.payload.get("planner_response")
                or event.payload.get("llm_plan_response")
                or ""
            )
            if raw_plan_response:
                plan = parse_structured_plan_response(raw_plan_response)
                planner_mode = "llm_structured_replan"
            else:
                # Deterministic replan: rebuild from goal + observation-aware snippets.
                plan = build_deterministic_plan(goal, specs)
                planner_mode = "deterministic_replan"

            if not plan.steps:
                # Fall back: if original plan present, return it stripped of failed step when possible.
                raw_prior = event.payload.get("plan")
                if isinstance(raw_prior, dict):
                    prior = ExecutionPlan.from_dict(raw_prior)
                    failed_index = int(event.payload.get("failed_index", 0) or 0)
                    remaining = prior.steps[failed_index + 1 :]
                    if remaining:
                        plan = ExecutionPlan(goal=goal, steps=remaining)
                        planner_mode = "skip_failed_step"
                    else:
                        plan = prior
                        planner_mode = "prior_plan_unchanged"

            self._bus.publish(
                PLAN_REPLAN_RESULT,
                {
                    "run_id": run_id,
                    "request_id": request_id,
                    "goal": goal,
                    "plan": plan.to_dict(),
                    "planner_mode": planner_mode,
                    "observation_snippets": wm_snippets,
                    "context_token_estimate": bundle.token_estimate,
                    "workspace_id": workspace_id,
                    "correlation": correlation.to_payload(),
                },
                source=self.name,
            )
            # Also emit PLAN_GENERATED for AppState / telemetry consistency.
            self._bus.publish(
                PLAN_GENERATED,
                {
                    "request_id": request_id,
                    "goal": goal,
                    "goal_id": "",
                    "plan": plan.to_dict(),
                    "planner_mode": planner_mode,
                    "replan": True,
                    "run_id": run_id,
                    "correlation": correlation.to_payload(),
                },
                source=self.name,
            )
        except Exception as exc:
            self._bus.publish(
                PLAN_REPLAN_RESULT,
                {
                    "run_id": run_id,
                    "request_id": request_id,
                    "error": str(exc),
                    "correlation": correlation.to_payload(),
                },
                source=self.name,
            )
