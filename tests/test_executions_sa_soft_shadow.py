"""Stage 2 SHADOW step 6a — Executions soft-shadow pins for State Authority."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_factory import build_services
from ai_command_center.db.connection import init_database
from ai_command_center.domain.state_authority import StateDelta, StateQuery
from ai_command_center.services.state_authority_service import StateAuthorityService


def test_build_services_wires_execution_run_event_query() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    names = set(wired.services.names())
    assert "execution_run" in names
    assert "execution_event" in names
    assert "execution_query" in names
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "execution_runs" in tables


def test_state_authority_has_no_execution_lookup() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)
    assert not hasattr(sa, "_execution_lookup")
    fields = getattr(StateQuery, "__dataclass_fields__", {})
    assert "include_executions" not in fields


def test_sa_mutate_does_not_support_execution_ops() -> None:
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
            workspace_id="ws-e",
            operations=({"op": "append_execution_run", "run_id": "run-1"},),
        )
    )
    assert receipt.ok is False
    assert "unsupported" in receipt.message.lower()
    sa.stop()
