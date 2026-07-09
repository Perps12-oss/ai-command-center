"""ExecutionEventRepository persistence tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository


def _repo(tmp_path: Path) -> tuple[ExecutionEventRepository, sqlite3.Connection]:
    conn = sqlite3.connect(tmp_path / "execution_events.db")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    return ExecutionEventRepository(conn), conn


def test_execution_event_repository_append_and_list() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo, conn = _repo(Path(tmp))
        try:
            first = repo.append(
                ExecutionEvent(
                    event_id="evt-1",
                    trace_id="trace-1",
                    parent_event_id=None,
                    timestamp=10.0,
                    event_type="chat.started",
                    actor="chat",
                    scope="chat",
                    request_id="req-1",
                    payload=(("model", "llama3"),),
                )
            )
            second = repo.append(
                ExecutionEvent(
                    event_id="evt-2",
                    trace_id="trace-1",
                    parent_event_id="evt-1",
                    timestamp=11.0,
                    event_type="chat.complete",
                    actor="chat",
                    scope="chat",
                    request_id="req-1",
                    payload=(("text", "done"),),
                )
            )
            assert first.event_id == "evt-1"
            assert second.parent_event_id == "evt-1"

            by_request = repo.list_by_request("req-1")
            assert [event.event_id for event in by_request] == ["evt-1", "evt-2"]
            assert by_request[1].payload_dict()["text"] == "done"

            by_trace = repo.list_by_trace("trace-1")
            assert len(by_trace) == 2

            recent = repo.list_recent()
            assert recent[-1].event_id == "evt-2"
        finally:
            conn.close()
