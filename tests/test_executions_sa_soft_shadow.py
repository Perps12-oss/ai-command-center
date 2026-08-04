"""Stage 2 SHADOW step 6a/6b — Executions soft-shadow pins for State Authority."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_factory import build_services
from ai_command_center.db.connection import init_database
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.state_authority import StateDelta, StateQuery
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository
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
    """ADR-017: executions remain outside SA.mutate (append-only elsewhere)."""
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


def test_execution_run_get_by_correlation_correlates_receipts() -> None:
    """6b — correlate execution receipts via correlation_id (repo API)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    repo = ExecutionRunRepository(conn)
    cid = "corr-exec-6b"
    correlation = CorrelationContext(correlation_id=cid)
    first = repo.append(
        request_id="req-1",
        source="test",
        snapshot={"goal_id": "g-1", "workflow_run_id": "wf-1"},
        correlation=correlation,
    )
    second = repo.append(
        request_id="req-2",
        source="test",
        snapshot={"goal_id": "g-1"},
        correlation=correlation,
    )
    other = repo.append(
        request_id="req-other",
        source="test",
        snapshot={},
        correlation=CorrelationContext(correlation_id="other-cid"),
    )
    hits = repo.get_by_correlation(cid)
    assert [r.run_id for r in hits] == [first.run_id, second.run_id]
    assert all(r.correlation.correlation_id == cid for r in hits)
    assert other.run_id not in {r.run_id for r in hits}
