"""Tests for telemetry payload sanitization / data protection."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_STARTED,
    TELEMETRY_EVENT,
)
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.services.telemetry_service import (
    TelemetryService,
    _sanitize_payload,
)


def test_sanitize_payload_redacts_sensitive_keys() -> None:
    """Sensitive leaf values are replaced with [REDACTED]."""
    payload = {
        "prompt": "secret prompt",
        "query": "secret query",
        "content": "secret content",
        "clipboard": "secret clipboard",
        "stdout": "secret output",
        "safe": "visible",
        "nested": {"api_key": "secret key", "ok": "visible"},
        "list": [{"token": "secret token"}, "plain"],
    }
    sanitized = _sanitize_payload(payload)
    assert sanitized["prompt"] == "[REDACTED]"
    assert sanitized["query"] == "[REDACTED]"
    assert sanitized["content"] == "[REDACTED]"
    assert sanitized["clipboard"] == "[REDACTED]"
    assert sanitized["stdout"] == "[REDACTED]"
    assert sanitized["safe"] == "visible"
    assert sanitized["nested"]["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["ok"] == "visible"
    assert sanitized["list"][0]["token"] == "[REDACTED]"
    assert sanitized["list"][1] == "plain"


def test_telemetry_service_redacts_chat_payload() -> None:
    """The service records a sanitized copy of chat events; no EventBus publication."""
    db = init_database(connect(Path(":memory:")))
    bus = EventBus()
    repo = TelemetryRepository(db)
    service = TelemetryService(bus, repo)
    service.start()

    published = []
    bus.subscribe(TELEMETRY_EVENT, published.append)

    bus.publish(
        CHAT_STARTED,
        {"prompt": "secret prompt", "query": "note query", "model": "llama3.2:3b"},
        source="chat",
    )

    assert len(published) == 0

    stored = repo.fetch_session(service.session_id)
    assert len(stored) >= 1
    raw = stored[0].payload_dict()
    assert raw["prompt"] == "[REDACTED]"
    assert raw["query"] == "[REDACTED]"
    assert raw["model"] == "llama3.2:3b"

    service.stop()
