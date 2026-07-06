"""Program 3 telemetry scope normalization and adoption metrics."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.context_manager import ContextBundle
from ai_command_center.core.events.topics import CHAT_COMPLETE, TELEMETRY_EVENT, TOOL_INVOKE, UI_COMMAND
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
)
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.services.telemetry_service import TelemetryService
from ai_command_center.services.telemetry_summary import compute_session_summary
from ai_command_center.core.event_bus import EventBus


def _repo() -> TelemetryRepository:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    return TelemetryRepository(conn)


def test_telemetry_normalizes_workspace_entity_scope() -> None:
    bus = EventBus()
    repo = _repo()
    events: list[dict] = []
    bus.subscribe(TELEMETRY_EVENT, lambda e: events.append(dict(e.payload)))
    service = TelemetryService(bus, repo)
    service.start()
    try:
        bus.publish(
            UI_COMMAND,
            {
                "text": "Summarize",
                "workspace_entity_id": "card-1",
                "workspace_id": "ws-1",
            },
            source="ui",
        )
        bus.publish(
            TOOL_INVOKE,
            {
                "tool": "shell",
                "workspace_context": {"workspace_id": "ws-2", "entity_id": "card-2"},
            },
            source="agent",
        )
    finally:
        service.stop()

    rows = repo.fetch_session(service.session_id)
    payloads = [row.payload_dict() for row in rows]
    assert any(p.get("workspace_id") == "ws-1" and p.get("entity_id") == "card-1" for p in payloads)
    assert any(p.get("workspace_id") == "ws-2" and p.get("entity_id") == "card-2" for p in payloads)
    assert any(e["payload"].get("entity_id") == "card-1" for e in events)


def test_session_summary_reports_workspace_scope_ratio() -> None:
    rows = [
        {
            "event": UI_COMMAND,
            "timestamp": "2026-07-05T00:00:00+00:00",
            "payload": {"text": "a", "workspace_id": "ws-1"},
        },
        {
            "event": CHAT_COMPLETE,
            "timestamp": "2026-07-05T00:00:01+00:00",
            "payload": {"request_id": "r1", "text": "done"},
        },
        {
            "event": TOOL_INVOKE,
            "timestamp": "2026-07-05T00:00:02+00:00",
            "payload": {"bundle": ContextBundle(prompt="x", sources=("user_query",), token_estimate=1)},
        },
    ]

    summary = compute_session_summary(rows)

    assert summary["workspace_scope"]["total"] == 2
    assert summary["workspace_scope"]["scoped"] == 1
    assert summary["workspace_scope"]["ratio_pct"] == 50.0
