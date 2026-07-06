"""Layer 1 — TruthBoundary unit tests (security-style, no providers/UI/LLM)."""

from __future__ import annotations

import pytest

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult
from ai_command_center.orchestration.receipts.execution_receipt import ExecutionReceipt
from ai_command_center.orchestration.verification.truth_boundary import TruthBoundary


def _receipt(
    *,
    intent: OrchestrationIntent,
    success: bool = True,
    facts: tuple[tuple[str, object], ...] = (),
    error: str | None = None,
) -> ExecutionReceipt:
    return ExecutionReceipt(
        receipt_id="r-unit",
        request_id="req-unit",
        intent=intent.value,
        provider_id="test",
        success=success,
        facts=facts,
        error=error,
    )


@pytest.fixture
def boundary() -> TruthBoundary:
    return TruthBoundary()


# --- happy path ---


def test_accepts_verified_launch(boundary: TruthBoundary) -> None:
    facts = {"application": "outlook", "launched": True}
    result = ProviderExecutionResult(success=True, response_text="Opened outlook.", facts=facts)
    receipt = _receipt(
        intent=OrchestrationIntent.LAUNCH_APPLICATION,
        facts=tuple(sorted(facts.items())),
    )
    validation = boundary.validate(OrchestrationIntent.LAUNCH_APPLICATION, result, receipt)
    assert validation.valid is True
    assert validation.response_source == "orchestration"


def test_accepts_time_fact(boundary: TruthBoundary) -> None:
    result = ProviderExecutionResult(
        success=True,
        response_text="It is 3:00 PM.",
        facts={"time": "3:00 PM"},
    )
    receipt = _receipt(intent=OrchestrationIntent.SYSTEM_TIME_QUERY)
    validation = boundary.validate(OrchestrationIntent.SYSTEM_TIME_QUERY, result, receipt)
    assert validation.valid is True
    assert "3:00 PM" in validation.response_text


def test_rejects_failed_execution(boundary: TruthBoundary) -> None:
    result = ProviderExecutionResult(success=False, error="boom")
    receipt = _receipt(
        intent=OrchestrationIntent.LAUNCH_APPLICATION,
        success=False,
        error="boom",
    )
    validation = boundary.validate(OrchestrationIntent.LAUNCH_APPLICATION, result, receipt)
    assert validation.valid is False
    assert validation.response_source == "orchestration_rejected"


# --- adversarial / security guarantees ---


def test_truth_boundary_blocks_unverified_email_sent(boundary: TruthBoundary) -> None:
    result = ProviderExecutionResult(
        success=True,
        response_text="Email sent successfully to the team.",
        facts={},
    )
    receipt = _receipt(intent=OrchestrationIntent.SEND_EMAIL, success=True, facts=())
    validation = boundary.validate(OrchestrationIntent.SEND_EMAIL, result, receipt)
    assert validation.valid is False
    assert validation.response_source == "orchestration_rejected"
    assert "verify" in validation.response_text.lower()


def test_outlook_opened_without_execution_receipt_is_rejected(boundary: TruthBoundary) -> None:
    result = ProviderExecutionResult(
        success=True,
        response_text="Opened outlook.",
        facts={"application": "outlook"},
    )
    receipt = _receipt(
        intent=OrchestrationIntent.LAUNCH_APPLICATION,
        facts=(("application", "outlook"),),
    )
    validation = boundary.validate(OrchestrationIntent.LAUNCH_APPLICATION, result, receipt)
    assert validation.valid is False
    assert validation.response_source == "orchestration_rejected"


def test_calendar_event_created_without_provider_confirmation_is_rejected(
    boundary: TruthBoundary,
) -> None:
    result = ProviderExecutionResult(
        success=True,
        response_text="Your event has been created.",
        facts={},
    )
    receipt = _receipt(intent=OrchestrationIntent.CALENDAR_EVENT_CREATE, success=True)
    validation = boundary.validate(OrchestrationIntent.CALENDAR_EVENT_CREATE, result, receipt)
    assert validation.valid is False
    assert validation.response_source == "orchestration_rejected"
    assert "verify" in validation.response_text.lower()


def test_email_sent_with_full_receipt_is_accepted(boundary: TruthBoundary) -> None:
    facts = {"email_sent": True, "message_id": "msg-1", "recipient": "boss@example.com"}
    result = ProviderExecutionResult(success=True, facts=facts)
    receipt = _receipt(
        intent=OrchestrationIntent.SEND_EMAIL,
        facts=tuple(sorted(facts.items())),
    )
    validation = boundary.validate(OrchestrationIntent.SEND_EMAIL, result, receipt)
    assert validation.valid is True


def test_receipt_result_success_mismatch_is_rejected(boundary: TruthBoundary) -> None:
    facts = {"application": "outlook", "launched": True}
    result = ProviderExecutionResult(success=True, facts=facts)
    receipt = _receipt(
        intent=OrchestrationIntent.LAUNCH_APPLICATION,
        success=False,
        error="launch failed",
        facts=tuple(sorted(facts.items())),
    )
    validation = boundary.validate(OrchestrationIntent.LAUNCH_APPLICATION, result, receipt)
    assert validation.valid is False
    assert "mismatch" in validation.detail.lower()


def test_llm_narrative_injection_with_empty_receipts_is_rejected(
    boundary: TruthBoundary,
) -> None:
    result = ProviderExecutionResult(
        success=True,
        response_text="Email sent! Your message is on its way.",
        facts={},
    )
    receipt = _receipt(intent=OrchestrationIntent.SEND_EMAIL, success=True, facts=())
    validation = boundary.validate(OrchestrationIntent.SEND_EMAIL, result, receipt)
    assert validation.valid is False
    assert validation.response_source == "orchestration_rejected"
