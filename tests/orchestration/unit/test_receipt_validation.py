"""Layer 1 — execution receipt validation (no providers/UI)."""

from __future__ import annotations

from ai_command_center.orchestration.execution.executor import OrchestrationExecutor
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.application_provider import ApplicationProvider
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
from ai_command_center.orchestration.receipts.execution_receipt import ExecutionReceipt


def test_execution_receipt_to_dict_round_trip_fields() -> None:
    receipt = ExecutionReceipt(
        receipt_id="rcpt-1",
        request_id="req-1",
        intent=OrchestrationIntent.LAUNCH_APPLICATION.value,
        provider_id="application",
        success=True,
        facts=(("application", "outlook"), ("launched", True)),
    )
    payload = receipt.to_dict()
    assert payload["receipt_id"] == "rcpt-1"
    assert payload["request_id"] == "req-1"
    assert payload["intent"] == "launch_application"
    assert payload["provider_id"] == "application"
    assert payload["success"] is True
    assert payload["facts"] == {"application": "outlook", "launched": True}


def test_executor_always_emits_receipt_even_when_provider_missing() -> None:
    registry = OrchestrationProviderRegistry()
    executor = OrchestrationExecutor(registry)
    run = executor.run(
        OrchestrationIntent.SEND_EMAIL,
        "email",
        request_id="req-missing",
        query="send email",
        args={},
    )
    assert run.receipt.request_id == "req-missing"
    assert run.receipt.provider_id == "email"
    assert run.receipt.intent == OrchestrationIntent.SEND_EMAIL.value
    assert run.receipt.success is False
    assert run.result.success is False


def test_executor_receipt_facts_match_result_facts() -> None:
    registry = OrchestrationProviderRegistry(
        application=ApplicationProvider(
            launch_fn=lambda app, argv: {"application": app, "launched": True},
        ),
    )
    executor = OrchestrationExecutor(registry)
    run = executor.run(
        OrchestrationIntent.LAUNCH_APPLICATION,
        "application",
        request_id="req-launch",
        query="open outlook",
        args={"application": "outlook"},
    )
    assert run.receipt.success is True
    assert dict(run.receipt.facts) == run.result.facts
