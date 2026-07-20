"""IdempotencyService — detect existing state and emit NO_OP plans."""

from __future__ import annotations

from typing import Any

from ai_command_center.domain.execution_result_type import ExecutionResultType
from ai_command_center.domain.planner_plan import ExecutionPlan, PlanStep
from ai_command_center.domain.state_context import StateContext
from ai_command_center.services.base import BaseService
from ai_command_center.core.state_intelligence.execution_intent_registry import ExecutionIntentRegistry
from ai_command_center.core.state_intelligence.world_model_query_service import WorldModelQueryService


class IdempotencyService(BaseService):
    """Checks WM + Intent before execution; may short-circuit with NO_OP."""

    name = "idempotency"

    def __init__(
        self,
        bus,
        *,
        query_service: WorldModelQueryService | None = None,
        intent_registry: ExecutionIntentRegistry | None = None,
    ) -> None:
        super().__init__(bus)
        self._query = query_service
        self._intents = intent_registry

    def _on_load(self) -> None:
        return

    def _on_unload(self) -> None:
        return

    def check(
        self,
        *,
        text: str,
        capability: str = "",
        state_context: StateContext | None = None,
        workspace_id: str = "",
    ) -> dict[str, Any]:
        """Return decision dict: action=proceed|no_op, optional virtual receipt."""
        needle = text.strip().lower()
        ws = workspace_id or (state_context.workspace_id if state_context else "")

        # In-flight duplicate → NO_OP cached.
        if self._intents is not None:
            match = self._intents.has_matching_intent(text, workspace_id=ws)
            if match is not None:
                return self._no_op_result(
                    text=text,
                    capability=capability or match.capability,
                    reason="in_flight_intent",
                    intent_id=match.intent_id,
                )

        ctx = state_context
        if ctx is None and self._query is not None:
            ctx = self._query.project_state(text=text, workspace_id=ws)

        if ctx is not None and self._state_already_holds(needle, capability, ctx):
            return self._no_op_result(
                text=text,
                capability=capability,
                reason="state_already_holds",
            )

        return {"action": "proceed", "result_type": ExecutionResultType.SUCCESS.value}

    def maybe_no_op_plan(
        self,
        *,
        text: str,
        capability: str = "",
        state_context: StateContext | None = None,
        workspace_id: str = "",
    ) -> ExecutionPlan | None:
        decision = self.check(
            text=text,
            capability=capability,
            state_context=state_context,
            workspace_id=workspace_id,
        )
        if decision.get("action") != "no_op":
            return None
        return ExecutionPlan(
            goal=text,
            steps=(
                PlanStep(
                    step_id="noop-1",
                    capability="system.noop",
                    args={
                        "result_type": ExecutionResultType.NO_OP.value,
                        "status": "SUCCESS_CACHED",
                        "reason": decision.get("reason", ""),
                        "original_capability": capability,
                    },
                    require_approval=False,
                ),
            ),
        )

    @staticmethod
    def _no_op_result(
        *,
        text: str,
        capability: str,
        reason: str,
        intent_id: str = "",
    ) -> dict[str, Any]:
        return {
            "action": "no_op",
            "result_type": ExecutionResultType.NO_OP.value,
            "status": "SUCCESS_CACHED",
            "reason": reason,
            "capability": capability,
            "text": text,
            "intent_id": intent_id,
            "virtual_receipt": {
                "success": True,
                "result_type": ExecutionResultType.NO_OP.value,
                "status": "SUCCESS_CACHED",
                "facts": (("cached", True), ("reason", reason)),
            },
        }

    @staticmethod
    def _state_already_holds(
        needle: str,
        capability: str,
        ctx: StateContext,
    ) -> bool:
        if not needle:
            return False
        # Create / remember / launch style duplicates against labeled entities.
        createish = capability in {
            "notes.create",
            "memory.store",
            "applications.launch",
            "launch_application",
            "goals.create",
            "tasks.create",
        } or needle.startswith(("create ", "remember:", "open ", "launch "))

        if not createish:
            return False

        for entity in ctx.entities:
            label = str(entity.get("label") or "").lower()
            if not label:
                continue
            if label in needle or needle in label:
                # Don't NO_OP against in-flight synthetic entities here —
                # those are handled by intent registry.
                if entity.get("type") == "execution_intent":
                    continue
                attrs = entity.get("attributes") or {}
                if attrs.get("in_flight"):
                    continue
                return True
        for memory in ctx.memories:
            label = str(memory.get("label") or "").lower()
            content = str(memory.get("content") or "").lower()
            if label and label in needle:
                return True
            if content and content in needle:
                return True
        return False
