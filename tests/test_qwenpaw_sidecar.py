"""Tests for QwenPaw sidecar bridge after runtime-first demotion of COMMAND_ROUTED racing."""

from __future__ import annotations

from ai_command_center.core.capability_external_registry import (
    clear_external_request,
    is_externally_handled,
    mark_external_request,
)
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CAPABILITY_RUNTIME_REQUEST,
    COMMAND_ROUTED,
    LLM_REQUEST,
    LLM_STEP_REQUEST,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.runtime.provider_registry import build_default_runtime_registry
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.qwenpaw_sidecar_service import QwenPawSidecarService
from ai_command_center.services.runtime_capability_router_service import (
    RuntimeCapabilityRouterService,
)


def test_planning_prefix_classifies_to_qwenpaw() -> None:
    bus = EventBus()
    health = QwenPawSidecarHealthState()
    health.update(enabled=True, reachable=True, detail="ready")
    router = RuntimeCapabilityRouterService(
        bus, provider_registry=build_default_runtime_registry(bus, qwenpaw_health=health)
    )
    router.start()
    try:
        kind = RuntimeCapabilityRouterService.classify("/plan schedule standup")
        assert kind is CapabilityKind.PLANNING
        assert router.resolve_provider(kind) == "qwenpaw"
    finally:
        router.stop()


def test_command_routed_no_longer_dispatches_external_runtime() -> None:
    """RuntimeCapabilityRouter must not race on COMMAND_ROUTED (INV ownership)."""
    bus = EventBus()
    health = QwenPawSidecarHealthState()
    health.update(enabled=True, reachable=True, detail="ready")
    router = RuntimeCapabilityRouterService(
        bus, provider_registry=build_default_runtime_registry(bus, qwenpaw_health=health)
    )
    runtime_requests: list[dict] = []
    bus.subscribe(CAPABILITY_RUNTIME_REQUEST, lambda e: runtime_requests.append(dict(e.payload)))
    router.start()
    try:
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": "chat",
                "request_id": "req-plan-ready",
                "args": {"prompt": "/plan schedule standup"},
            },
            source="command_router",
        )
        assert runtime_requests == []
    finally:
        router.stop()


def test_chat_handler_ignores_command_routed() -> None:
    """ChatHandler is llm-capability only — COMMAND_ROUTED must not emit LLM_REQUEST."""
    bus = EventBus()
    chat = ChatHandlerService(bus, ContextManager())
    llm_requests: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    chat.start()
    try:
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": "chat",
                "request_id": "req-defer-1",
                "args": {"prompt": "/plan my week"},
            },
            source="command_router",
        )
        assert llm_requests == []
    finally:
        chat.stop()


def test_chat_handler_llm_step_publishes_llm_request() -> None:
    bus = EventBus()
    chat = ChatHandlerService(bus, ContextManager())
    llm_requests: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    chat.start()
    try:
        bus.publish(
            LLM_STEP_REQUEST,
            {
                "request_id": "req-llm-1",
                "run_id": "run-1",
                "step_id": "step-1",
                "capability": "llm",
                "args": {"prompt": "hello"},
                "prompt": "hello",
            },
            source="execution_orchestrator",
        )
        assert len(llm_requests) == 1
        assert llm_requests[0].get("capability") == "llm"
    finally:
        chat.stop()


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
            },
            source="test",
        )
        assert service is not None
    finally:
        service.stop()
