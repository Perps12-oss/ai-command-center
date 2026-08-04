"""Stage 2 closeout — Agents soft-shadow pins (ADR-013)."""

from __future__ import annotations

import inspect
import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_factory import build_services
from ai_command_center.db.connection import init_database
from ai_command_center.domain.state_authority import StateDelta
from ai_command_center.services.state_authority_service import StateAuthorityService


def test_build_services_wires_agent_runtime_not_coordinator() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    names = set(wired.services.names())
    assert "agent_runtime" in names
    assert "planner" in names
    source = inspect.getsource(build_services)
    assert "AgentCoordinator" not in source
    assert "PlanningEngine" not in source


def test_state_authority_has_no_agent_lookup() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)
    assert not hasattr(sa, "_agent_lookup")


def test_sa_mutate_does_not_support_agent_ops() -> None:
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
            workspace_id="ws-a",
            operations=({"op": "spawn_agent", "agent_id": "a-1"},),
        )
    )
    assert receipt.ok is False
    assert "unsupported" in receipt.message.lower()
    sa.stop()
