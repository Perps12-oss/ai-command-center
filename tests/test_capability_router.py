"""Tests for RuntimeCapabilityRouterService (Agent Runtime Interface Phase 1)."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT, INTENT_SHELL
from ai_command_center.core.events.topics import (
    CAPABILITY_CLASSIFIED,
    CAPABILITY_DISPATCH,
    CAPABILITY_FALLBACK,
    COMMAND_ROUTED,
)
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.runtime.provider_registry import build_default_runtime_registry
from ai_command_center.services.runtime_capability_router_service import RuntimeCapabilityRouterService


def _start_router(bus: EventBus) -> RuntimeCapabilityRouterService:
    router = RuntimeCapabilityRouterService(bus, provider_registry=build_default_runtime_registry(bus))
    router.start()
    return router


def test_classify_prefix_and_hints() -> None:
    assert RuntimeCapabilityRouterService.classify("/plan my week") == CapabilityKind.PLANNING
    assert RuntimeCapabilityRouterService.classify("/code fix auth") == CapabilityKind.CODING
    assert RuntimeCapabilityRouterService.classify("what's on my calendar today") == CapabilityKind.CHAT
    assert RuntimeCapabilityRouterService.classify("hello there") == CapabilityKind.CHAT


def test_chat_routed_emits_capability_events() -> None:
    bus = EventBus()
    router = _start_router(bus)
    classified: list[dict] = []
    dispatched: list[dict] = []
    bus.subscribe(CAPABILITY_CLASSIFIED, lambda e: classified.append(dict(e.payload)))
    bus.subscribe(CAPABILITY_DISPATCH, lambda e: dispatched.append(dict(e.payload)))
    try:
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "args": {"prompt": "hello"},
                "request_id": "req-chat-1",
            },
            source="command_router",
        )
        assert len(classified) == 1
        assert classified[0]["kind"] == CapabilityKind.CHAT.value
        assert classified[0]["provider_id"] == "native"
        assert len(dispatched) == 1
        assert dispatched[0]["fallback_provider_id"] == "native"
    finally:
        router.stop()


def test_planning_routes_to_qwenpaw_and_falls_back_when_unavailable() -> None:
    bus = EventBus()
    router = _start_router(bus)
    classified: list[dict] = []
    fallbacks: list[dict] = []
    bus.subscribe(CAPABILITY_CLASSIFIED, lambda e: classified.append(dict(e.payload)))
    bus.subscribe(CAPABILITY_FALLBACK, lambda e: fallbacks.append(dict(e.payload)))
    try:
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "args": {"prompt": "plan my week"},
                "request_id": "req-plan-1",
            },
            source="command_router",
        )
        assert len(classified) == 1
        assert classified[0]["kind"] == CapabilityKind.PLANNING.value
        assert classified[0]["provider_id"] == "qwenpaw"
        assert len(fallbacks) == 1
        assert fallbacks[0]["fallback_provider_id"] == "native"
        assert "sidecar" in fallbacks[0]["reason"].lower()
    finally:
        router.stop()


def test_non_chat_intent_ignored() -> None:
    bus = EventBus()
    router = _start_router(bus)
    classified: list[dict] = []
    bus.subscribe(CAPABILITY_CLASSIFIED, lambda e: classified.append(dict(e.payload)))
    try:
        bus.publish(
            COMMAND_ROUTED,
            {"intent": INTENT_SHELL, "args": {"command": "echo hi"}},
            source="command_router",
        )
        assert classified == []
    finally:
        router.stop()


def test_wrong_source_ignored() -> None:
    bus = EventBus()
    router = _start_router(bus)
    classified: list[dict] = []
    bus.subscribe(CAPABILITY_CLASSIFIED, lambda e: classified.append(dict(e.payload)))
    try:
        bus.publish(
            COMMAND_ROUTED,
            {"intent": INTENT_CHAT, "args": {"prompt": "hello"}},
            source="test",
        )
        assert classified == []
    finally:
        router.stop()
