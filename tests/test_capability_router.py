"""Tests for RuntimeCapabilityRouterService (Agent Runtime Interface Phase 1).

COMMAND_ROUTED racing was removed — router is a classifier/settings helper.
External dispatch is owned by ExecutionOrchestrator via CAPABILITY_RUNTIME_REQUEST.
"""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import SETTINGS_SNAPSHOT
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


def test_resolve_provider_defaults_native_for_chat() -> None:
    bus = EventBus()
    router = _start_router(bus)
    try:
        assert router.resolve_provider(CapabilityKind.CHAT) == "native"
        assert router.resolve_provider(CapabilityKind.PLANNING) == "qwenpaw"
    finally:
        router.stop()


def test_settings_snapshot_updates_provider_map() -> None:
    bus = EventBus()
    router = _start_router(bus)
    try:
        bus.publish(
            SETTINGS_SNAPSHOT,
            {"capability_provider_planning": "native"},
            source="test",
        )
        assert router.resolve_provider(CapabilityKind.PLANNING) == "native"
    finally:
        router.stop()
