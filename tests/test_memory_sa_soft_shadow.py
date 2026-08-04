"""Stage 2 SHADOW step 4 — Memory soft-shadow pins for State Authority.

ADR-015: ``store_memory`` is the first non-WM ``SA.mutate`` op (step 4d).
"""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    MEMORY_LOOKUP_RESULT,
    MEMORY_SELECTED,
    MEMORY_STORED,
    WORLD_MODEL_MUTATION_APPLIED,
)
from ai_command_center.core.service_factory import build_services
from ai_command_center.db.connection import init_database
from ai_command_center.domain.state_authority import StateDelta, StateQuery
from ai_command_center.services.memory_graph_service import MemoryGraphService
from ai_command_center.services.state_authority_service import StateAuthorityService


def test_build_services_wires_memory_lookup_for_state() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)
    assert sa._memory_lookup is not None
    assert getattr(sa._memory_lookup, "__func__", None) is MemoryGraphService.lookup_for_state
    assert sa._memory_store is not None
    assert getattr(sa._memory_store, "__func__", None) is MemoryGraphService.store_memory
    assert "memory_graph" in set(wired.services.names())


def test_lookup_for_state_does_not_publish_memory_bus_events() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    mgs = wired.services.get("memory_graph")
    assert isinstance(mgs, MemoryGraphService)
    mgs.store_memory("pin alpha memory for SA", workspace_id="ws-1")

    seen: list[str] = []
    for topic in (MEMORY_LOOKUP_RESULT, MEMORY_SELECTED, MEMORY_STORED):
        bus.subscribe(topic, lambda e, t=topic: seen.append(t))

    hits = mgs.lookup_for_state("alpha", workspace_id="ws-1")
    assert hits
    assert seen == []


def test_sa_query_include_memories_uses_lookup() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    mgs = wired.services.get("memory_graph")
    sa = wired.services.get("state_authority")
    assert isinstance(mgs, MemoryGraphService)
    assert isinstance(sa, StateAuthorityService)
    mgs.store_memory("durable recall token zebra", workspace_id="ws-m")
    sa.start()
    projection = sa.query(
        StateQuery(text="zebra", workspace_id="ws-m", include_memories=True)
    )
    assert projection.memories
    blob = " ".join(str(m) for m in projection.memories).lower()
    assert "zebra" in blob
    sa.stop()


def test_sa_mutate_store_memory_round_trip() -> None:
    """ADR-015: store_memory via SA.mutate → memory_nodes; no WM dual-write."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)

    wm_events: list[str] = []
    bus.subscribe(WORLD_MODEL_MUTATION_APPLIED, lambda e: wm_events.append(e.topic))

    sa.start()
    receipt = sa.mutate(
        StateDelta(
            workspace_id="ws-m",
            operations=(
                {
                    "op": "store_memory",
                    "body": "adr015pin | durable recall token mango",
                },
            ),
        )
    )
    assert receipt.ok is True
    assert receipt.applied
    assert receipt.applied[0]["op"] == "store_memory"
    assert receipt.applied[0].get("memory_id")
    assert wm_events == []

    projection = sa.query(
        StateQuery(text="mango", workspace_id="ws-m", include_memories=True)
    )
    assert projection.memories
    blob = " ".join(str(m) for m in projection.memories).lower()
    assert "mango" in blob
    sa.stop()


def test_sa_mutate_store_memory_rejects_empty_body() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)
    sa.start()
    receipt = sa.mutate(
        StateDelta(
            workspace_id="ws-m",
            operations=({"op": "store_memory", "body": ""},),
        )
    )
    assert receipt.ok is False
    assert "body required" in receipt.message.lower()
    sa.stop()


def test_sa_mutate_still_rejects_workflow_style_goal_lifecycle() -> None:
    """Lifecycle goal ops stay outside SA (ADR-016 = submit_goal only)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)
    sa.start()
    receipt = sa.mutate(
        StateDelta(
            workspace_id="ws-g",
            operations=({"op": "cancel_goal", "goal_id": "g-1"},),
        )
    )
    assert receipt.ok is False
    assert "unsupported" in receipt.message.lower()
    sa.stop()
