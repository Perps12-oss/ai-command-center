"""ExecutionRunService tests."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import ORCHESTRATION_RUN_SNAPSHOT
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository
from ai_command_center.services.execution_run_service import ExecutionRunService


def test_persists_orchestration_snapshot() -> None:
    db = init_database(connect(Path(":memory:")))
    repo = ExecutionRunRepository(db)
    bus = EventBus()
    svc = ExecutionRunService(bus, repo=repo)
    svc.start()
    bus.publish(
        ORCHESTRATION_RUN_SNAPSHOT,
        {"request_id": "req-x", "intent": "system_time_query"},
        source="test",
    )
    svc.stop()
    runs = repo.list_by_request("req-x")
    assert len(runs) == 1
    assert runs[0].source == "orchestration"
