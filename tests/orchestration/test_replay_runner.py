"""ReplayRunner tests."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.db.connection import connect, init_database
from ai_command_center.orchestration.replay.replay_runner import ReplayRunner
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository


def _runner() -> ReplayRunner:
    db = init_database(connect(Path(":memory:")))
    repo = ExecutionRunRepository(db)
    return ReplayRunner(repo)


def test_replay_timeline_orders_stages() -> None:
    runner = _runner()
    repo = runner._repo
    repo.append(
        request_id="req-1",
        source="orchestration",
        snapshot={"intent": "system_time_query", "provider_id": "system_facts"},
    )
    repo.append(
        request_id="req-1",
        source="chat",
        snapshot={"text": "done"},
    )
    timeline = runner.build_timeline("req-1")
    assert timeline.request_id == "req-1"
    assert len(timeline.stages) == 2
    assert timeline.provider_ids == ("system_facts",)
