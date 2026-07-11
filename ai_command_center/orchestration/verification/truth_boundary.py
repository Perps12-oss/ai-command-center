"""Truth boundary — blocks ungrounded orchestration responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
        mismatch = self._receipt_result_mismatch(result, receipt)
        if mismatch is not None:
            return mismatch

        if not receipt.success or not result.success:
            detail = result.error or receipt.error or "execution failed"
            return TruthValidation(
                valid=False,
                detail=detail,
                response_text=f"I could not complete that action: {detail}",
                response_source="orchestration_rejected",
            )

        narrative_reject = self._reject_ungrounded_narrative(intent, result)
        if narrative_reject is not None:
            return narrative_reject

        if intent is OrchestrationIntent.SYSTEM_TIME_QUERY:
            return self._validate_time(result)
        if intent is OrchestrationIntent.LAUNCH_APPLICATION:
            return self._validate_launch(result)
        if intent is OrchestrationIntent.CALENDAR_QUERY:
            return self._validate_calendar_query(result)
        if intent is OrchestrationIntent.SEND_EMAIL:
            return self._validate_email_sent(result, receipt)
        if intent is OrchestrationIntent.CALENDAR_EVENT_CREATE:
            return self._validate_calendar_event_created(result, receipt)
        if intent is OrchestrationIntent.EXECUTE_SHELL:
            return self._validate_shell(result)

        return TruthValidation(
            valid=False,
            detail=f"unsupported intent {intent.value}",
            response_text="That request is not supported.",
            response_source="orchestration_rejected",
        )

    @staticmethod
    def _receipt_facts(receipt: ExecutionReceipt) -> dict[str, Any]:
        return dict(receipt.facts)

    def _receipt_result_mismatch(
        self,
        result: ProviderExecutionResult,
        receipt: ExecutionReceipt,
    ) -> TruthValidation | None:
        if receipt.success != result.success:
            return TruthValidation(
                valid=False,
                detail="receipt/result success mismatch",
                response_text="I could not verify that action completed.",
                response_source="orchestration_rejected",
            )

        receipt_facts = self._receipt_facts(receipt)
        if not receipt_facts:
            return None

        for key, value in receipt_facts.items():
            if key not in result.facts:
                return TruthValidation(
                    valid=False,
                    detail=f"receipt fact missing in result: {key}",
                    response_text="I could not verify that action completed.",
                    response_source="orchestration_rejected",
                )
            if result.facts.get(key) != value:
                return TruthValidation(
                    valid=False,
                    detail=f"receipt/result fact mismatch: {key}",
                    response_text="I could not verify that action completed.",
                    response_source="orchestration_rejected",
                )
        return None

    @staticmethod
    def _reject_ungrounded_narrative(
        intent: OrchestrationIntent,
        result: ProviderExecutionResult,
    ) -> TruthValidation | None:
        """Reject LLM-style success narratives when required facts are absent."""
        text = result.response_text.strip().lower()
        facts = result.facts

        if intent is OrchestrationIntent.SEND_EMAIL:
            if _claims_email_sent(text) and not _email_receipt_confirmed(facts):
                return TruthValidation(
                    valid=False,
                    detail="email sent narrative without receipt",
                    response_text="I could not verify that the email was sent.",
                    response_source="orchestration_rejected",
                )
        if intent is OrchestrationIntent.LAUNCH_APPLICATION:
            if _claims_app_opened(text) and facts.get("launched") is not True:
                return TruthValidation(
                    valid=False,
                    detail="launch narrative without execution receipt",
                    response_text="Application launch could not be verified.",
                    response_source="orchestration_rejected",
                )
        if intent is OrchestrationIntent.CALENDAR_EVENT_CREATE:
            if _claims_calendar_event_created(text) and not _calendar_create_confirmed(facts):
                return TruthValidation(
                    valid=False,
                    detail="calendar create narrative without provider confirmation",
                    response_text="I could not verify that the calendar event was created.",
                    response_source="orchestration_rejected",
                )
        return None

    @staticmethod
    def _validate_time(result: ProviderExecutionResult) -> TruthValidation:
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

    @staticmethod
    def _validate_launch(result: ProviderExecutionResult) -> TruthValidation:
        app = str(result.facts.get("application", "")).strip()
        launched = result.facts.get("launched")
        if not app or launched is not True:
            return TruthValidation(
                valid=False,
                detail="launch not verified",
                response_text="Application launch could not be verified.",
                response_source="orchestration_rejected",
            )
        return TruthValidation(
            valid=True,
            detail="launch receipt verified",
            response_text=result.response_text or f"Opened {app}.",
            response_source="orchestration",
        )

    @staticmethod
    def _validate_calendar_query(result: ProviderExecutionResult) -> TruthValidation:
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

    def _validate_email_sent(
        self,
        result: ProviderExecutionResult,
        receipt: ExecutionReceipt,
    ) -> TruthValidation:
        if not _email_receipt_confirmed(result.facts):
            return TruthValidation(
                valid=False,
                detail="email receipt missing",
                response_text="I could not verify that the email was sent.",
                response_source="orchestration_rejected",
            )
        receipt_facts = self._receipt_facts(receipt)
        if not _email_receipt_confirmed(receipt_facts):
            return TruthValidation(
                valid=False,
                detail="email provider confirmation missing",
                response_text="I could not verify that the email was sent.",
                response_source="orchestration_rejected",
            )
        recipient = str(result.facts.get("recipient", "")).strip()
        return TruthValidation(
            valid=True,
            detail="email receipt verified",
            response_text=result.response_text or f"Email sent to {recipient}.",
            response_source="orchestration",
        )

    def _validate_calendar_event_created(
        self,
        result: ProviderExecutionResult,
        receipt: ExecutionReceipt,
    ) -> TruthValidation:
        if not _calendar_create_confirmed(result.facts):
            return TruthValidation(
                valid=False,
                detail="calendar event confirmation missing",
                response_text="I could not verify that the calendar event was created.",
                response_source="orchestration_rejected",
            )
        receipt_facts = self._receipt_facts(receipt)
        if not _calendar_create_confirmed(receipt_facts):
            return TruthValidation(
                valid=False,
                detail="calendar provider confirmation missing",
                response_text="I could not verify that the calendar event was created.",
                response_source="orchestration_rejected",
            )
        title = str(result.facts.get("title", "")).strip() or "event"
        return TruthValidation(
            valid=True,
            detail="calendar event receipt verified",
            response_text=result.response_text or f"Created calendar event: {title}.",
            response_source="orchestration",
        )

    @staticmethod
    def _validate_shell(result: ProviderExecutionResult) -> TruthValidation:
        """Validate shell execution — requires success flag and command fact."""
        success = result.facts.get("success")
        if success is not True:
            return TruthValidation(
                valid=False,
                detail="shell execution not confirmed",
                response_text=result.response_text
                or "Shell command could not be verified.",
                response_source="orchestration_rejected",
            )
        command = str(result.facts.get("command", "")).strip()
        output = str(result.facts.get("output", "")).strip()
        response_text = result.response_text.strip() if result.response_text else output
        return TruthValidation(
            valid=True,
            detail="shell execution receipt verified",
            response_text=response_text or f"Ran: {command}",
            response_source="orchestration",
        )


def _claims_email_sent(text: str) -> bool:
    return "email sent" in text or "sent the email" in text or "message sent" in text


def _claims_app_opened(text: str) -> bool:
    return text.startswith("opened ") or "outlook opened" in text or "launched " in text


def _claims_calendar_event_created(text: str) -> bool:
    return (
        "calendar event created" in text
        or "created a calendar event" in text
        or "event has been created" in text
        or "scheduled the meeting" in text
    )


def _email_receipt_confirmed(facts: dict[str, Any]) -> bool:
    if facts.get("email_sent") is not True:
        return False
    message_id = str(facts.get("message_id", "")).strip()
    recipient = str(facts.get("recipient", "")).strip()
    return bool(message_id or recipient)


def _calendar_create_confirmed(facts: dict[str, Any]) -> bool:
    if facts.get("event_created") is not True:
        return False
    return bool(str(facts.get("event_id", "")).strip())
