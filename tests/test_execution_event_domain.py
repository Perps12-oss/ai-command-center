"""ExecutionEvent domain contract tests."""

from __future__ import annotations

from ai_command_center.domain.execution_event import ExecutionEvent


def test_execution_event_bus_payload_roundtrip() -> None:
    event = ExecutionEvent(
        event_id="evt-1",
        trace_id="trace-1",
        parent_event_id="evt-0",
        timestamp=123.4,
        event_type="chat.complete",
        actor="chat",
        scope="chat",
        request_id="req-1",
        payload=(("text", "hello"), ("model", "llama3")),
        state_diff=(("status", "complete"),),
    )
    restored = ExecutionEvent.from_bus_payload(event.to_bus_payload())
    assert restored.event_id == "evt-1"
    assert restored.trace_id == "trace-1"
    assert restored.parent_event_id == "evt-0"
    assert restored.event_type == "chat.complete"
    assert restored.payload_dict() == {"text": "hello", "model": "llama3"}
    assert restored.state_diff_dict() == {"status": "complete"}
