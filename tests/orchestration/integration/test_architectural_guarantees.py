"""Layer 2 — architectural guarantee integration tests.

Intent → ExecutionAuthority → Plan → Orchestrator → Receipt pipeline.
No GUI. These tests encode runtime guarantees for CI.
"""

from __future__ import annotations

import re

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_COMPLETE,
    LLM_REQUEST,
    LLM_STEP_REQUEST,
    ORCHESTRATION_RECEIPT,
)

from tests.orchestration.conftest import publish_chat, start_runtime_stack

_COMMAND_SYNTAX_PATTERNS = (
    re.compile(r"\btype\s+outlook\b", re.IGNORECASE),
    re.compile(r"\brun\s+", re.IGNORECASE),
    re.compile(r"\bcmd\b", re.IGNORECASE),
    re.compile(r"```"),
    re.compile(r"/\w+"),  # slash-command documentation
)


def _assert_no_command_documentation(text: str) -> None:
    for pattern in _COMMAND_SYNTAX_PATTERNS:
        assert not pattern.search(text), f"response looks like command docs: {text!r}"


def _start(bus: EventBus, *, calendar_connected: bool = False):
    return start_runtime_stack(bus, calendar_connected=calendar_connected)


@pytest.mark.orchestration
def test_calendar_query_without_provider_does_not_hallucinate(bus: EventBus) -> None:
    orchestration, chat, authority = _start(bus)
    completes: list[dict] = []
    llm_requests: list[dict] = []
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    try:
        publish_chat(bus, "What's on my calendar?", request_id="req-cal-1")
        assert len(completes) >= 1
        text = str(completes[-1]["text"]).lower()
        assert "not connected" in text or "could not" in text
        assert completes[-1]["truth_validated"] is True
        assert "meeting with" not in text
        assert "standup" not in text
        assert llm_requests == []
    finally:
        chat.stop()
        orchestration.stop()
        authority.stop()


@pytest.mark.orchestration
def test_open_outlook_requires_execution_receipt(bus: EventBus) -> None:
    orchestration, chat, authority = _start(bus)
    completes: list[dict] = []
    receipts: list[dict] = []
    llm_requests: list[dict] = []
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    try:
        publish_chat(bus, "Open Outlook", request_id="req-outlook-1")
        assert len(receipts) == 1
        assert receipts[0]["success"] is True
        assert "outlook" in str(receipts[0]["facts"]).lower() or receipts[0][
            "intent"
        ] == "launch_application"

        assert len(completes) >= 1
        assert completes[-1]["truth_validated"] is True
        assert "Opened outlook" in str(completes[-1]["text"])
        _assert_no_command_documentation(str(completes[-1]["text"]))
        assert llm_requests == []
    finally:
        chat.stop()
        orchestration.stop()
        authority.stop()


@pytest.mark.orchestration
def test_create_calendar_event_without_connection_never_claims_success(bus: EventBus) -> None:
    orchestration, chat, authority = _start(bus, calendar_connected=False)
    completes: list[dict] = []
    receipts: list[dict] = []
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))
    try:
        publish_chat(
            bus,
            "Create shopping event today at 14:00",
            request_id="req-create-1",
        )
        assert len(receipts) == 1
        assert receipts[0]["intent"] in {"calendar_event_create", "execution_run"}
        assert len(completes) >= 1
        text = str(completes[-1]["text"]).lower()
        assert "your event has been created" not in text
        assert "created calendar event" not in text or completes[-1]["truth_validated"] is False
    finally:
        chat.stop()
        orchestration.stop()
        authority.stop()


@pytest.mark.orchestration
def test_create_calendar_event_with_mock_provider_generates_verified_receipt(
    bus: EventBus,
) -> None:
    orchestration, chat, authority = _start(bus, calendar_connected=True)
    completes: list[dict] = []
    receipts: list[dict] = []
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))
    try:
        publish_chat(
            bus,
            "Create shopping event today at 14:00",
            request_id="req-create-2",
        )
        assert len(receipts) == 1
        assert receipts[0]["success"] is True
        assert len(completes) >= 1
        assert completes[-1]["truth_validated"] is True
        assert "shopping" in str(completes[-1]["text"]).lower()
    finally:
        chat.stop()
        orchestration.stop()
        authority.stop()


@pytest.mark.orchestration
def test_time_query_returns_system_fact_not_command(bus: EventBus) -> None:
    orchestration, chat, authority = _start(bus)
    completes: list[dict] = []
    llm_requests: list[dict] = []
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    try:
        publish_chat(bus, "What time is it?", request_id="req-time-1")
        assert len(completes) >= 1
        text = str(completes[-1]["text"])
        assert text.startswith("It is ")
        assert "July" in text
        _assert_no_command_documentation(text)
        assert llm_requests == []
    finally:
        chat.stop()
        orchestration.stop()
        authority.stop()


@pytest.mark.orchestration
def test_truth_boundary_blocks_unverified_email_sent_in_pipeline(bus: EventBus) -> None:
    """Force a model-style success narrative through a stub email provider path."""
    from ai_command_center.orchestration.execution.executor import OrchestrationExecutor
    from ai_command_center.orchestration.execution.response_composer import ResponseComposer
    from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
    from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult
    from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
    from ai_command_center.orchestration.routing.intent_router import IntentRouter
    from ai_command_center.orchestration.verification.truth_boundary import TruthBoundary

    class LyingEmailProvider:
        provider_id = "email"

        def health(self) -> tuple[bool, str]:
            return True, "ready"

        def execute(self, intent, *, request_id, query, args) -> ProviderExecutionResult:
            return ProviderExecutionResult(
                success=True,
                response_text="Email sent successfully.",
                facts={},
            )

    registry = OrchestrationProviderRegistry()
    registry._providers["email"] = LyingEmailProvider()  # type: ignore[assignment]

    intent = OrchestrationIntent.SEND_EMAIL
    provider_id = IntentRouter.resolve_provider(intent)
    assert provider_id == "email"
    executor = OrchestrationExecutor(registry)
    boundary = TruthBoundary()
    composer = ResponseComposer()

    run = executor.run(
        intent,
        provider_id,
        request_id="req-email-adv",
        query="send email",
        args={},
    )
    validation = boundary.validate(intent, run.result, run.receipt)
    composed = composer.compose(
        intent=intent,
        provider_id=provider_id,
        validation=validation,
        receipt=run.receipt,
    )

    assert validation.valid is False
    assert composed.truth_valid is False
    assert composed.response_source == "orchestration_rejected"
    assert "verify" in composed.text.lower()


def test_unhandled_chat_becomes_explicit_llm_capability_step(bus: EventBus) -> None:
    """Conversational text is planned as an explicit llm capability step."""
    orchestration, chat, authority = _start(bus)
    llm_requests: list[dict] = []
    step_requests: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    bus.subscribe(LLM_STEP_REQUEST, lambda e: step_requests.append(dict(e.payload)))
    try:
        publish_chat(bus, "Tell me a joke", request_id="req-joke-1")
        assert len(step_requests) == 1
        assert step_requests[0]["capability"] == "llm"
        assert len(llm_requests) == 1
        assert llm_requests[0].get("capability") == "llm"
    finally:
        chat.stop()
        orchestration.stop()
        authority.stop()
