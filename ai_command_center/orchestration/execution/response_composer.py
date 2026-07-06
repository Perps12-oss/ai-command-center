"""Composes verified orchestration responses for chat.complete."""

from __future__ import annotations

from dataclasses import dataclass

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.receipts.execution_receipt import ExecutionReceipt
from ai_command_center.orchestration.verification.truth_boundary import TruthValidation


@dataclass(frozen=True, slots=True)
class ComposedResponse:
    text: str
    response_source: str
    truth_valid: bool
    receipt: ExecutionReceipt
    intent: OrchestrationIntent
    provider_id: str
    truth_detail: str


class ResponseComposer:
    """Single approved path for orchestrated CHAT_COMPLETE payloads."""

    def compose(
        self,
        *,
        intent: OrchestrationIntent,
        provider_id: str,
        validation: TruthValidation,
        receipt: ExecutionReceipt,
    ) -> ComposedResponse:
        return ComposedResponse(
            text=validation.response_text,
            response_source=validation.response_source,
            truth_valid=validation.valid,
            receipt=receipt,
            intent=intent,
            provider_id=provider_id,
            truth_detail=validation.detail,
        )

    def to_chat_complete_payload(
        self,
        composed: ComposedResponse,
        *,
        request_id: str,
    ) -> dict[str, object]:
        return {
            "request_id": request_id,
            "text": composed.text,
            "response_source": composed.response_source,
            "truth_validated": composed.truth_valid,
            "orchestration": {
                "intent": composed.intent.value,
                "provider_id": composed.provider_id,
                "receipt_id": composed.receipt.receipt_id,
                "truth_detail": composed.truth_detail,
            },
        }
