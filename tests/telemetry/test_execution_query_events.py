"""ExecutionQueryService event timeline tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import EXECUTION_QUERY_REQUEST, EXECUTION_QUERY_RESULT
from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository
from ai_command_center.services.execution_query_service import ExecutionQueryService


def _service(tmp_path: Path) -> tuple[EventBus, ExecutionQueryService, sqlite3.Connection]:
    conn = sqlite3.connect(tmp_path / "execution_query.db")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    run_repo = ExecutionRunRepository(conn)
    event_repo = ExecutionEventRepository(conn)
    bus = EventBus()
    service = ExecutionQueryService(bus, run_repo=run_repo, event_repo=event_repo)
    return bus, service, conn


def test_execution_query_returns_event_timeline() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bus, service, conn = _service(Path(tmp))
        try:
            event_repo = ExecutionEventRepository(conn)
            event_repo.append(
                ExecutionEvent(
                    event_id="evt-1",
                    trace_id="trace-1",
                    parent_event_id=None,
                    timestamp=1.0,
                    event_type="chat.complete",
                    actor="chat",
                    scope="chat",
                    request_id="req-q",
                    payload=(("text", "hello"),),
                )
            )
            results: list[dict] = []
            bus.subscribe(EXECUTION_QUERY_RESULT, lambda e: results.append(dict(e.payload)))
            service.start()
            bus.publish(EXECUTION_QUERY_REQUEST, {"request_id": "req-q"}, source="test")
            service.stop()
            assert results
            assert results[0]["timeline_source"] == "events"
            assert len(results[0]["execution_events"]) == 1
            assert results[0]["execution_events"][0]["event_id"] == "evt-1"
        finally:
            conn.close()
