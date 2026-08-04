"""Stage 2 Memory 4b — Assembler decision memory reads via State Authority."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.capability_context_assembler import CapabilityContextAssembler
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import MEMORY_LOOKUP_REQUEST
from ai_command_center.core.service_factory import build_services
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.db.connection import init_database
from ai_command_center.domain.state_authority import StateQuery
from ai_command_center.repositories.memory_repository import MemoryRepository
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.memory_graph_service import MemoryGraphService
from ai_command_center.services.state_authority_service import StateAuthorityService


def test_factory_binds_state_authority_onto_assembler() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    chat = wired.services.get("chat_handler")
    assert isinstance(sa, StateAuthorityService)
    assert chat is not None
    assembler = chat._assembler
    assert isinstance(assembler, CapabilityContextAssembler)
    assert assembler._state_authority is sa


def test_assembler_uses_sa_query_not_memory_lookup_request() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    memory = MemoryGraphService(bus, MemoryRepository(conn))
    memory.store_memory("assembler sa token mango", workspace_id="ws-a")
    sa = StateAuthorityService(
        bus,
        WorldModel(SQLiteWorldModelRepository(conn)),
        memory_lookup=memory.lookup_for_state,
    )
    seen: list[str] = []
    bus.subscribe(MEMORY_LOOKUP_REQUEST, lambda e: seen.append("hit"))

    assembler = CapabilityContextAssembler(
        bus, ContextManager(), state_authority=sa
    )
    assembled = assembler.assemble_for_command(
        request_id="req-4b",
        query="mango",
        event_payload={"workspace_id": "ws-a"},
        args={},
        source="test",
        include_model_resolve=False,
    )
    assert seen == []
    # ContextManager places graph snippets in prompt/sources — assert SA path ran.
    projection = sa.query(
        StateQuery(text="mango", workspace_id="ws-a", include_memories=True)
    )
    assert projection.memories
    assert any("mango" in str(m).lower() for m in projection.memories)
    # Assembled graph content should include memory when SA returns hits.
    assert "mango" in assembled.bundle.prompt.lower() or any(
        "mango" in str(s).lower() for s in assembled.bundle.sources
    )


def test_assembler_without_sa_still_publishes_memory_lookup_request() -> None:
    bus = EventBus()
    seen: list[dict] = []

    def _on_req(event) -> None:
        seen.append(dict(event.payload or {}))
        bus.publish(
            "memory.lookup.result",
            {
                "request_id": event.payload.get("request_id"),
                "snippets": ["[memory:legacy]\nfallback"],
            },
            source="test",
        )

    bus.subscribe(MEMORY_LOOKUP_REQUEST, _on_req)
    assembler = CapabilityContextAssembler(bus, ContextManager())
    assembled = assembler.assemble_for_command(
        request_id="req-legacy",
        query="fallback",
        event_payload={},
        args={},
        source="test",
        include_model_resolve=False,
    )
    assert seen and seen[0].get("query") == "fallback"
    assert "fallback" in assembled.bundle.prompt.lower() or any(
        "fallback" in str(s).lower() for s in assembled.bundle.sources
    )
