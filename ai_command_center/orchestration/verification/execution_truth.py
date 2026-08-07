"""Map planner capabilities to TruthBoundary intents (ADR-021)."""

from __future__ import annotations

from typing import Any

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult
from ai_command_center.orchestration.receipts.execution_receipt import ExecutionReceipt
from ai_command_center.orchestration.verification.truth_boundary import (
    TruthBoundary,
    TruthValidation,
)

_CAPABILITY_TO_INTENT: dict[str, OrchestrationIntent] = {
    "shell": OrchestrationIntent.EXECUTE_SHELL,
    "execute_shell": OrchestrationIntent.EXECUTE_SHELL,
    "launch_application": OrchestrationIntent.LAUNCH_APPLICATION,
    "system_time_query": OrchestrationIntent.SYSTEM_TIME_QUERY,
    "calendar_query": OrchestrationIntent.CALENDAR_QUERY,
    "send_email": OrchestrationIntent.SEND_EMAIL,
    "calendar_event_create": OrchestrationIntent.CALENDAR_EVENT_CREATE,
}


def map_capability_to_intent(capability: str) -> OrchestrationIntent:
    key = str(capability or "").strip().lower()
    return _CAPABILITY_TO_INTENT.get(key, OrchestrationIntent.UNHANDLED)


def enrich_execution_facts(
    *,
    facts: dict[str, Any],
    plan: dict[str, Any],
    step_outputs: list[Any],
    success: bool,
) -> dict[str, Any]:
    """Add TruthBoundary-required keys from plan args and provider step facts."""
    out = dict(facts)
    out["success"] = success
    steps = list(plan.get("steps") or [])
    first_step = steps[0] if steps and isinstance(steps[0], dict) else {}
    args = dict(first_step.get("args") or {})
    if "command" in args and "command" not in out:
        out["command"] = args.get("command")
    if "application" in args and "application" not in out:
        out["application"] = args.get("application")
    if step_outputs and isinstance(step_outputs[0], dict):
        first_out = step_outputs[0]
        if first_out.get("output") and "output" not in out:
            out["output"] = first_out.get("output")
        if first_out.get("success") is True:
            out["success"] = True
        # Provider facts (time/launched/events/…) travel on step_outputs when tools
        # return ToolResult.facts — required for TruthBoundary after ADR-021 wire.
        raw_facts = first_out.get("facts")
        if isinstance(raw_facts, dict):
            for key, value in raw_facts.items():
                out.setdefault(key, value)
    capability = str(first_step.get("capability") or out.get("capability") or "").strip().lower()
    if capability == "launch_application" and out.get("success") is True:
        if "application" in out and out.get("launched") is None:
            out["launched"] = True
    return out


def validate_execution_truth(
    *,
    capability: str,
    success: bool,
    error: str,
    response_text: str,
    facts: dict[str, Any],
    receipt: ExecutionReceipt,
    boundary: TruthBoundary | None = None,
) -> TruthValidation:
    """Run TruthBoundary for known intents; generic success gate otherwise."""
    intent = map_capability_to_intent(capability)
    if intent is OrchestrationIntent.UNHANDLED:
        if success:
            return TruthValidation(
                valid=True,
                detail="execution run completed",
                response_text=response_text or "Done.",
                response_source="execution",
            )
        detail = error or "execution failed"
        return TruthValidation(
            valid=False,
            detail=detail,
            response_text=f"I could not complete that action: {detail}",
            response_source="execution_rejected",
        )

    result = ProviderExecutionResult(
        success=success,
        response_text=response_text,
        facts=dict(facts),
        error=error or None,
    )
    return (boundary or TruthBoundary()).validate(intent, result, receipt)


__all__ = [
    "map_capability_to_intent",
    "enrich_execution_facts",
    "validate_execution_truth",
]
