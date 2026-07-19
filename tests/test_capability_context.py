"""Tests for context assembly before external capability invoke (ARI Phase 3)."""

from __future__ import annotations

from ai_command_center.core.capability_context_assembler import (
    CapabilityContextAssembler,
    context_bundle_to_dict,
)
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ENTITY_CONTEXT_REQUEST,
    ENTITY_CONTEXT_RESULT,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
)


def _wire_sync_handlers(bus: EventBus) -> None:
    def _memory_lookup(event) -> None:
        bus.publish(
            MEMORY_LOOKUP_RESULT,
            {
                "request_id": event.payload["request_id"],
                "snippets": ["Memory: standup is at 9am"],
            },
            source="test",
        )

    def _session_history(event) -> None:
        bus.publish(
            SESSION_HISTORY_RESULT,
            {
                "request_id": event.payload["request_id"],
                "history": [("user", "prior turn")],
            },
            source="test",
        )

    def _entity_context(event) -> None:
        bus.publish(
            ENTITY_CONTEXT_RESULT,
            {
                "request_id": event.payload["request_id"],
                "snippets": ["Workspace card: Team standup"],
            },
            source="test",
        )

    bus.subscribe(MEMORY_LOOKUP_REQUEST, _memory_lookup)
    bus.subscribe(SESSION_HISTORY_REQUEST, _session_history)
    bus.subscribe(ENTITY_CONTEXT_REQUEST, _entity_context)


def test_external_context_bundle_can_be_built_before_runtime_request() -> None:
    bus = EventBus()
    _wire_sync_handlers(bus)
    assembler = CapabilityContextAssembler(bus, ContextManager())
    assembled = assembler.assemble_for_command(
        request_id="req-ctx-1",
        query="/plan schedule standup",
        event_payload={"workspace_entity_id": "ent-1"},
        args={},
        source="test",
        include_model_resolve=False,
    )
    bundle = context_bundle_to_dict(assembled.bundle)
    prompt = str(bundle.get("prompt", ""))
    assert prompt
    assert "schedule standup" in prompt
    assert "Memory: standup is at 9am" in prompt
    assert "prior turn" in prompt
    assert "Team standup" in prompt
    assert bundle.get("token_estimate", 0) > 0


def test_assembler_publishes_lookup_requests_synchronously() -> None:
    bus = EventBus()
    memory_requests: list[dict] = []
    session_requests: list[dict] = []

    def _memory(event) -> None:
        memory_requests.append(dict(event.payload))
        bus.publish(
            MEMORY_LOOKUP_RESULT,
            {"request_id": event.payload["request_id"], "snippets": []},
            source="test",
        )

    def _session(event) -> None:
        session_requests.append(dict(event.payload))
        bus.publish(
            SESSION_HISTORY_RESULT,
            {"request_id": event.payload["request_id"], "history": []},
            source="test",
        )

    bus.subscribe(MEMORY_LOOKUP_REQUEST, _memory)
    bus.subscribe(SESSION_HISTORY_REQUEST, _session)

    assembler = CapabilityContextAssembler(bus, ContextManager())
    assembled = assembler.assemble_for_command(
        request_id="req-sync-1",
        query="hello world",
        event_payload={"workspace_id": "ws-1"},
        args={},
        source="test",
        include_model_resolve=False,
    )
    assert memory_requests[0]["request_id"] == "req-sync-1"
    assert memory_requests[0]["workspace_id"] == "ws-1"
    assert session_requests[0]["request_id"] == "req-sync-1"
    assert assembled.bundle.prompt
    assert "hello world" in assembled.bundle.prompt
