"""Truth boundary — blocks ungrounded orchestration responses."""

from __future__ import annotations

from dataclasses import dataclass

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult
from ai_command_center.orchestration.receipts.execution_receipt import ExecutionReceipt


@dataclass(frozen=True, slots=True)
class TruthValidation:
    valid: bool
    detail: str
    response_text: str
    response_source: str


class TruthBoundary:
    """Validates that a user-facing response is grounded in execution facts."""

    def validate(
        self,
        intent: OrchestrationIntent,
        result: ProviderExecutionResult,
        receipt: ExecutionReceipt,
    ) -> TruthValidation:
        if not receipt.success or not result.success:
            detail = result.error or receipt.error or "execution failed"
            return TruthValidation(
                valid=False,
                detail=detail,
                response_text=f"I could not complete that action: {detail}",
                response_source="orchestration_rejected",
            )

        if intent is OrchestrationIntent.SYSTEM_TIME_QUERY:
            time_value = str(result.facts.get("time", "")).strip()
            if not time_value:
                return TruthValidation(
                    valid=False,
                    detail="missing time fact",
                    response_text="I could not determine the current time.",
                    response_source="orchestration_rejected",
                )
            return TruthValidation(
                valid=True,
                detail="time fact present",
                response_text=result.response_text or f"The current time is {time_value}.",
                response_source="orchestration",
            )

        if intent is OrchestrationIntent.LAUNCH_APPLICATION:
            app = str(result.facts.get("application", "")).strip()
            if not app:
                return TruthValidation(
                    valid=False,
                    detail="missing application fact",
                    response_text="Application launch could not be verified.",
                    response_source="orchestration_rejected",
                )
            return TruthValidation(
                valid=True,
                detail="launch receipt verified",
                response_text=result.response_text or f"Opened {app}.",
                response_source="orchestration",
            )

        if intent is OrchestrationIntent.CALENDAR_QUERY:
            if result.facts.get("connected") is False:
                return TruthValidation(
                    valid=True,
                    detail="calendar disconnected — truthful fallback",
                    response_text=result.response_text
                    or "Your calendar is not connected. Connect a calendar provider in settings.",
                    response_source="orchestration",
                )
            events = result.facts.get("events")
            if events is None:
                return TruthValidation(
                    valid=False,
                    detail="calendar facts missing",
                    response_text="I could not read your calendar.",
                    response_source="orchestration_rejected",
                )
            return TruthValidation(
                valid=True,
                detail="calendar facts present",
                response_text=result.response_text or "Here is what I found on your calendar.",
                response_source="orchestration",
            )

        return TruthValidation(
            valid=False,
            detail=f"unsupported intent {intent.value}",
            response_text="That request is not supported.",
            response_source="orchestration_rejected",
        )
