"""Shared fixtures for orchestration integration tests (mock providers, no GUI/LLM)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import COMMAND_ROUTED
from ai_command_center.orchestration.providers.application_provider import ApplicationProvider
from ai_command_center.orchestration.providers.calendar_provider import CalendarProvider
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
from ai_command_center.orchestration.providers.system_facts_provider import SystemFactsProvider
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.orchestration_service import OrchestrationService


def fixed_now() -> datetime:
    return datetime(2026, 7, 6, 14, 30, tzinfo=timezone.utc)


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


def build_registry(
    *,
    calendar_connected: bool = False,
) -> OrchestrationProviderRegistry:
    return OrchestrationProviderRegistry(
        system_facts=SystemFactsProvider(now_fn=fixed_now),
        application=ApplicationProvider(
            launch_fn=lambda app, argv: {"application": app, "launched": True},
        ),
        calendar=CalendarProvider(connected=calendar_connected),
    )


@pytest.fixture
def orchestration_stack(bus: EventBus) -> tuple[OrchestrationService, ChatHandlerService]:
    registry = build_registry()
    orchestration = OrchestrationService(bus, provider_registry=registry)
    chat = ChatHandlerService(bus, ContextManager())
    orchestration.start()
    chat.start()
    yield orchestration, chat
    chat.stop()
    orchestration.stop()


def publish_chat(bus: EventBus, prompt: str, *, request_id: str = "req-orch") -> None:
    bus.publish(
        COMMAND_ROUTED,
        {
            "intent": INTENT_CHAT,
            "args": {"prompt": prompt},
            "request_id": request_id,
        },
        source="command_router",
    )
