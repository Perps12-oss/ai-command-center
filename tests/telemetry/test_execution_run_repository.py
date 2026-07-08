"""ExecutionRunRepository tests."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository


def _repo() -> ExecutionRunRepository:
    db = init_database(connect(Path(":memory:")))
    return ExecutionRunRepository(db)


def test_append_and_fetch_by_request() -> None:
    repo = _repo()
    run = repo.append(
        request_id="req-1",
        source="orchestration",
        snapshot={"intent": "system_facts", "provider_id": "system_facts"},
    )
    assert run.run_id
    assert run.request_id == "req-1"
    rows = repo.list_by_request("req-1")
    assert len(rows) == 1
    assert rows[0].snapshot["intent"] == "system_facts"
