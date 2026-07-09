"""Planner layer — converts goals into execution manifests without executing."""

from __future__ import annotations

import re
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
                    "error": "goal is required",
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

            # TODO(Phase C): parse structured JSON plan from LLM via ModelRouter/Ollama.
            plan = build_deterministic_plan(goal, specs)
            if not plan.steps:
                self._bus.publish(
                    PLAN_FAILED,
                    {
                        "request_id": request_id,
                        "goal": goal,
                        "error": "no capabilities available for goal",
                    },
                    source=self.name,
                )
                return

            self._bus.publish(
                PLAN_GENERATED,
                {
                    "request_id": request_id,
                    "goal": goal,
                    "plan": plan.to_dict(),
                    "planner_mode": "deterministic",
                    "context_version": bundle.version,
                    "context_token_estimate": bundle.token_estimate,
                },
                source=self.name,
            )
        except Exception as exc:
            self._bus.publish(
                PLAN_FAILED,
                {
                    "request_id": request_id,
                    "goal": goal,
                    "error": str(exc),
                },
                source=self.name,
            )
