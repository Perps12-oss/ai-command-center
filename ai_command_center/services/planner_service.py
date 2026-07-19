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
    PLAN_REQUEST,
    WORKSPACE_CONTEXT_REQUEST,
    WORKSPACE_CONTEXT_RESULT,
)
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
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
    """Subscribes to plan.request and publishes plan.generated — never executes."""

    name = "planner"

    def __init__(self, bus, *, context_manager: ContextManager) -> None:
        super().__init__(bus)
        self._context_manager = context_manager
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(PLAN_REQUEST, self._on_plan_request)
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
            workspace_snippets: list[str] = []
            if workspace_id:
                workspace_snippets = self._fetch_workspace_snippets(
                    request_id,
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                )

            specs = self._fetch_capability_specs(request_id, entity_types)

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
