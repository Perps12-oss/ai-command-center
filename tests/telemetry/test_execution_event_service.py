"""ExecutionEventService bus integration tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_COMPLETE,
    EXECUTION_EVENT_APPENDED,
    EXECUTION_EVENTS_LOADED,
    TOOL_RESULT,
)
from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.repositories.database_bootstrap_repository import DatabaseBootstrapRepository
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository
from ai_command_center.services.execution_event_service import ExecutionEventService


def _service(tmp_path: Path) -> tuple[EventBus, ExecutionEventService, ExecutionEventRepository, sqlite3.Connection]:
    conn = sqlite3.connect(tmp_path / "execution_event_service.db")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    repo = ExecutionEventRepository(conn)
    bus = EventBus()
    service = ExecutionEventService(bus, repo=repo)
    return bus, service, repo, conn


def test_chat_complete_appends_execution_event() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bus, service, repo, conn = _service(Path(tmp))
        try:
            appended: list[dict] = []
            bus.subscribe(EXECUTION_EVENT_APPENDED, lambda e: appended.append(dict(e.payload)))
            service.start()
            bus.publish(
                CHAT_COMPLETE,
                {
                    "request_id": "req-chat",
                    "text": "Answer text",
                    "model": "llama3",
                },
                source="chat",
            )
            service.stop()
            assert appended
            assert appended[0]["event_type"] == CHAT_COMPLETE
            assert appended[0]["request_id"] == "req-chat"
            rows = repo.list_by_request("req-chat")
            assert len(rows) == 1
            assert rows[0].payload_dict()["text"] == "Answer text"
        finally:
            conn.close()


def test_tool_result_chains_parent_event_id() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bus, service, repo, conn = _service(Path(tmp))
        try:
            service.start()
            bus.publish(
                TOOL_RESULT,
                {
                    "success": True,
                    "tool": "shell",
                    "invoke_id": "inv-1",
                    "output": "ok",
                    "request_id": "req-tool",
                },
                source="tool",
            )
            bus.publish(
                CHAT_COMPLETE,
                {"request_id": "req-tool", "text": "done"},
                source="chat",
            )
            service.stop()
            rows = repo.list_by_request("req-tool")
            assert len(rows) == 2
            assert rows[0].parent_event_id is None
            assert rows[1].parent_event_id == rows[0].event_id
        finally:
            conn.close()


def test_startup_publishes_recent_execution_events() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bus, service, repo, conn = _service(Path(tmp))
        try:
            repo.append(
                ExecutionEvent(
                    event_id="seed-1",
                    trace_id="trace-seed",
                    parent_event_id=None,
                    timestamp=1.0,
                    event_type="chat.complete",
                    actor="chat",
                    scope="chat",
                    request_id="req-seed",
                    payload=(("text", "seed"),),
                )
            )
            loaded: list[dict] = []
            bus.subscribe(EXECUTION_EVENTS_LOADED, lambda e: loaded.append(dict(e.payload)))
            service.start()
            service.stop()
            assert loaded
            events = loaded[0]["events"]
            assert len(events) == 1
            assert events[0]["event_id"] == "seed-1"
        finally:
            conn.close()
