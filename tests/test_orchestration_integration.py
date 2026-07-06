"""Integration tests for truth-bound orchestration service."""

from __future__ import annotations

from datetime import datetime, timezone

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CAPABILITY_CLASSIFIED,
    CHAT_COMPLETE,
    COMMAND_ROUTED,
    LLM_REQUEST,
    ORCHESTRATION_RECEIPT,
)
from ai_command_center.orchestration.providers.application_provider import ApplicationProvider
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
from ai_command_center.orchestration.providers.system_facts_provider import SystemFactsProvider
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.core.context_manager import ContextManager


def _fixed_now() -> datetime:
    return datetime(2026, 7, 6, 14, 30, tzinfo=timezone.utc)


def _start_stack(bus: EventBus) -> tuple[OrchestrationService, ChatHandlerService]:
    registry = OrchestrationProviderRegistry(
        system_facts=SystemFactsProvider(now_fn=_fixed_now),
        application=ApplicationProvider(
            launch_fn=lambda app, argv: {"application": app, "launched": True},
        ),
    )
    orchestration = OrchestrationService(bus, provider_registry=registry)
    chat = ChatHandlerService(bus, ContextManager())
    orchestration.start()
    chat.start()
    return orchestration, chat


def _publish_chat(bus: EventBus, prompt: str, request_id: str = "req-orch-1") -> None:
    bus.publish(
        COMMAND_ROUTED,
        {
            "intent": INTENT_CHAT,
            "args": {"prompt": prompt},
            "request_id": request_id,
        },
        source="command_router",
    )


def test_open_outlook_orchestrated_without_llm() -> None:
    bus = EventBus()
    orchestration, chat = _start_stack(bus)
    completes: list[dict] = []
    llm_requests: list[dict] = []
    receipts: list[dict] = []
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    bus.subscribe(ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload)))
    try:
        _publish_chat(bus, "Open Outlook", request_id="req-outlook")
        assert len(completes) == 1
        assert completes[0]["response_source"] == "orchestration"
        assert completes[0]["truth_validated"] is True
        assert "Opened outlook" in str(completes[0]["text"])
        assert llm_requests == []
        assert len(receipts) == 1
        assert receipts[0]["provider_id"] == "application"
        assert receipts[0]["success"] is True
    finally:
        chat.stop()
        orchestration.stop()


def test_what_time_is_it_without_llm() -> None:
    bus = EventBus()
    orchestration, chat = _start_stack(bus)
    completes: list[dict] = []
    llm_requests: list[dict] = []
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    try:
        _publish_chat(bus, "What time is it?", request_id="req-time")
        assert len(completes) == 1
        assert completes[0]["response_source"] == "orchestration"
        assert str(completes[0]["text"]).startswith("It is ")
        assert "July" in str(completes[0]["text"])
        assert llm_requests == []
    finally:
        chat.stop()
        orchestration.stop()


def test_calendar_disconnected_truthful_response() -> None:
    bus = EventBus()
    orchestration, chat = _start_stack(bus)
    completes: list[dict] = []
    capability_events: list[dict] = []
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    bus.subscribe(CAPABILITY_CLASSIFIED, lambda e: capability_events.append(dict(e.payload)))
    try:
        _publish_chat(bus, "What's on my calendar?", request_id="req-cal")
        assert len(completes) == 1
        assert "not connected" in str(completes[0]["text"]).lower()
        assert completes[0]["truth_validated"] is True
        assert capability_events == []
    finally:
        chat.stop()
        orchestration.stop()


def test_unhandled_defers_to_chat_handler() -> None:
    bus = EventBus()
    orchestration, chat = _start_stack(bus)
    llm_requests: list[dict] = []
    completes: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))
    try:
        _publish_chat(bus, "Tell me a joke", request_id="req-joke")
        assert len(llm_requests) == 1
        assert completes == []
    finally:
        chat.stop()
        orchestration.stop()
