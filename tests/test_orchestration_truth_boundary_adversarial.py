"""Adversarial tests for orchestration truth boundary hardening."""

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
        receipt_id="r-adv",
        request_id="req-adv",
        intent=intent.value,
        provider_id="test",
        success=success,
        facts=facts,
        error=error,
    )


@pytest.fixture
def boundary() -> TruthBoundary:
    return TruthBoundary()


def test_email_sent_narrative_without_receipt_is_rejected(boundary: TruthBoundary) -> None:
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


def test_email_sent_with_partial_receipt_is_rejected(boundary: TruthBoundary) -> None:
    result = ProviderExecutionResult(
        success=True,
        response_text="Done.",
        facts={"email_sent": True},
    )
    receipt = _receipt(
        intent=OrchestrationIntent.SEND_EMAIL,
        facts=(("email_sent", True),),
    )
    validation = boundary.validate(OrchestrationIntent.SEND_EMAIL, result, receipt)
    assert validation.valid is False
    assert "receipt" in validation.detail.lower() or "confirmation" in validation.detail.lower()


def test_email_sent_with_full_receipt_is_accepted(boundary: TruthBoundary) -> None:
    facts = {"email_sent": True, "message_id": "msg-1", "recipient": "boss@example.com"}
    result = ProviderExecutionResult(success=True, facts=facts)
    receipt = _receipt(
        intent=OrchestrationIntent.SEND_EMAIL,
        facts=tuple(sorted(facts.items())),
    )
    validation = boundary.validate(OrchestrationIntent.SEND_EMAIL, result, receipt)
    assert validation.valid is True
    assert validation.response_source == "orchestration"


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


def test_outlook_opened_with_launched_fact_is_accepted(boundary: TruthBoundary) -> None:
    facts = {"application": "outlook", "launched": True}
    result = ProviderExecutionResult(success=True, facts=facts)
    receipt = _receipt(
        intent=OrchestrationIntent.LAUNCH_APPLICATION,
        facts=tuple(sorted(facts.items())),
    )
    validation = boundary.validate(OrchestrationIntent.LAUNCH_APPLICATION, result, receipt)
    assert validation.valid is True


def test_calendar_event_created_without_provider_confirmation_is_rejected(
    boundary: TruthBoundary,
) -> None:
    result = ProviderExecutionResult(
        success=True,
        response_text="I created a calendar event for tomorrow.",
        facts={},
    )
    receipt = _receipt(intent=OrchestrationIntent.CALENDAR_EVENT_CREATE, success=True)
    validation = boundary.validate(OrchestrationIntent.CALENDAR_EVENT_CREATE, result, receipt)
    assert validation.valid is False
    assert validation.response_source == "orchestration_rejected"


def test_calendar_event_created_with_confirmation_is_accepted(boundary: TruthBoundary) -> None:
    facts = {"event_created": True, "event_id": "evt-42", "title": "Standup"}
    result = ProviderExecutionResult(success=True, facts=facts)
    receipt = _receipt(
        intent=OrchestrationIntent.CALENDAR_EVENT_CREATE,
        facts=tuple(sorted(facts.items())),
    )
    validation = boundary.validate(OrchestrationIntent.CALENDAR_EVENT_CREATE, result, receipt)
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


def test_receipt_fact_mismatch_is_rejected(boundary: TruthBoundary) -> None:
    result = ProviderExecutionResult(
        success=True,
        facts={"application": "outlook", "launched": True},
    )
    receipt = _receipt(
        intent=OrchestrationIntent.LAUNCH_APPLICATION,
        facts=(("application", "notepad"), ("launched", True)),
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
