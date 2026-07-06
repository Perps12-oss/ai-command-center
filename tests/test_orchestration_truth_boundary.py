"""Tests for orchestration truth boundary."""

from __future__ import annotations

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult
from ai_command_center.orchestration.receipts.execution_receipt import ExecutionReceipt
from ai_command_center.orchestration.verification.truth_boundary import TruthBoundary


def test_rejects_failed_execution() -> None:
    boundary = TruthBoundary()
    result = ProviderExecutionResult(success=False, error="boom")
    receipt = ExecutionReceipt(
        receipt_id="r1",
        request_id="req1",
        intent=OrchestrationIntent.LAUNCH_APPLICATION.value,
        provider_id="application",
        success=False,
        error="boom",
    )
    validation = boundary.validate(
        OrchestrationIntent.LAUNCH_APPLICATION,
        result,
        receipt,
    )
    assert validation.valid is False
    assert validation.response_source == "orchestration_rejected"


def test_accepts_time_fact() -> None:
    boundary = TruthBoundary()
    result = ProviderExecutionResult(
        success=True,
        response_text="It is 3:00 PM.",
        facts={"time": "3:00 PM"},
    )
    receipt = ExecutionReceipt(
        receipt_id="r2",
        request_id="req2",
        intent=OrchestrationIntent.SYSTEM_TIME_QUERY.value,
        provider_id="system_facts",
        success=True,
    )
    validation = boundary.validate(
        OrchestrationIntent.SYSTEM_TIME_QUERY,
        result,
        receipt,
    )
    assert validation.valid is True
    assert validation.response_source == "orchestration"
    assert "3:00 PM" in validation.response_text
