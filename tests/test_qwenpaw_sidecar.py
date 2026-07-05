"""Tests for QwenPaw sidecar bridge and external chat deferral."""

from __future__ import annotations

from ai_command_center.core.capability_external_registry import (
    clear_external_request,
    is_externally_handled,
    mark_external_request,
)
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CAPABILITY_RUNTIME_REQUEST,
    CHAT_STARTED,
    COMMAND_ROUTED,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.runtime.provider_registry import build_default_runtime_registry
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState
from ai_command_center.services.capability_router_service import CapabilityRouterService
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.qwenpaw_sidecar_service import QwenPawSidecarService


def test_qwenpaw_ready_invokes_runtime_request() -> None:
    bus = EventBus()
    health = QwenPawSidecarHealthState()
    health.update(enabled=True, reachable=True, detail="ready")
    router = CapabilityRouterService(
        bus, provider_registry=build_default_runtime_registry(bus, qwenpaw_health=health)
    )
    runtime_requests: list[dict] = []
    bus.subscribe(CAPABILITY_RUNTIME_REQUEST, lambda e: runtime_requests.append(dict(e.payload)))
    router.start()
    try:
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "request_id": "req-plan-ready",
                "args": {"prompt": "/plan schedule standup"},
            },
            source="command_router",
        )
        assert len(runtime_requests) == 1
        assert runtime_requests[0]["provider_id"] == "qwenpaw"
        assert is_externally_handled("req-plan-ready")
    finally:
        router.stop()
        clear_external_request("req-plan-ready")


def test_chat_handler_defers_when_external_request_active() -> None:
    bus = EventBus()
    health = QwenPawSidecarHealthState()
    health.update(enabled=True, reachable=True, detail="ready")
    router = CapabilityRouterService(
        bus, provider_registry=build_default_runtime_registry(bus, qwenpaw_health=health)
    )
    chat = ChatHandlerService(bus, ContextManager())
    chat_started: list[dict] = []
    bus.subscribe(CHAT_STARTED, lambda e: chat_started.append(dict(e.payload)))
    router.start()
    chat.start()
    try:
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "request_id": "req-defer-1",
                "args": {"prompt": "/plan my week"},
            },
            source="command_router",
        )
        assert is_externally_handled("req-defer-1")
        assert chat_started == []
    finally:
        chat.stop()
        router.stop()
        clear_external_request("req-defer-1")


def test_external_registry_mark_and_clear() -> None:
    mark_external_request("req-x")
    assert is_externally_handled("req-x")
    clear_external_request("req-x")
    assert not is_externally_handled("req-x")


def test_sidecar_service_subscribes_to_runtime_requests() -> None:
    bus = EventBus()
    health = QwenPawSidecarHealthState()
    service = QwenPawSidecarService(bus, health_state=health)
    service.start()
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {
                "qwenpaw_enabled": True,
                "qwenpaw_url": "http://127.0.0.1:8088",
                "qwenpaw_agent_id": "default",
            },
            source="test",
        )
        bus.publish(
            CAPABILITY_RUNTIME_REQUEST,
            {
                "request_id": "req-bridge-1",
                "provider_id": "qwenpaw",
                "kind": "planning",
                "query": "plan lunch",
            },
            source="qwenpaw",
        )
    finally:
        service.stop()
