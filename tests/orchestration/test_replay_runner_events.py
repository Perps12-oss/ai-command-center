"""ReplayRunner execution event stream tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.orchestration.replay.replay_runner import ReplayRunner
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository
from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository


def _runner(tmp_path: Path) -> tuple[ReplayRunner, ExecutionRunRepository, ExecutionEventRepository, sqlite3.Connection]:
    conn = sqlite3.connect(tmp_path / "replay.db")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    run_repo = ExecutionRunRepository(conn)
    event_repo = ExecutionEventRepository(conn)
    return ReplayRunner(run_repo, event_repo=event_repo), run_repo, event_repo, conn


def test_replay_runner_prefers_execution_events() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runner, run_repo, event_repo, conn = _runner(Path(tmp))
        try:
            run_repo.append(
                request_id="req-1",
                source="orchestration",
                snapshot={"intent": "legacy_intent"},
            )
            event_repo.append(
                ExecutionEvent(
                    event_id="evt-1",
                    trace_id="trace-1",
                    parent_event_id=None,
                    timestamp=1.0,
                    event_type="chat.started",
                    actor="chat",
                    scope="chat",
                    request_id="req-1",
                    payload=(("model", "llama3"),),
                )
            )
            event_repo.append(
                ExecutionEvent(
                    event_id="evt-2",
                    trace_id="trace-1",
                    parent_event_id="evt-1",
                    timestamp=2.0,
                    event_type="chat.complete",
                    actor="chat",
                    scope="chat",
                    request_id="req-1",
                    payload=(("text", "done"),),
                )
            )
            timeline = runner.build_timeline("req-1")
            assert timeline.source == "events"
            assert len(timeline.stages) == 2
            assert timeline.stages[0].event_id == "evt-1"
            assert timeline.stages[1].stage == "chat"
        finally:
            conn.close()


def test_replay_runner_falls_back_to_execution_runs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runner, run_repo, _event_repo, conn = _runner(Path(tmp))
        try:
            run_repo.append(
                request_id="req-2",
                source="chat",
                snapshot={"text": "legacy"},
            )
            timeline = runner.build_timeline("req-2")
            assert timeline.source == "runs"
            assert len(timeline.stages) == 1
            assert timeline.stages[0].stage == "chat"
        finally:
            conn.close()
