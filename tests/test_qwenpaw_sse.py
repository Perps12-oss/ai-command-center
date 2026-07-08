"""Unit tests for QwenPaw SSE parser."""

from __future__ import annotations

from ai_command_center.runtime.qwenpaw_sse import QwenPawStreamStatus, parse_sse_data_line


def test_parse_sse_extracts_incremental_delta() -> None:
    first = (
        'data: {"status":"in_progress","output":[{"role":"assistant","content":'
        '[{"type":"text","text":"Hello"}]}]}'
    )
    second = (
        'data: {"status":"in_progress","output":[{"role":"assistant","content":'
        '[{"type":"text","text":"Hello world"}]}]}'
    )
    event1 = parse_sse_data_line(first)
    assert event1 is not None
    assert event1.delta == "Hello"
    assert event1.status == QwenPawStreamStatus.IN_PROGRESS

    event2 = parse_sse_data_line(second, previous_text=event1.assistant_text)
    assert event2 is not None
    assert event2.delta == " world"
    assert event2.assistant_text == "Hello world"


def test_parse_sse_completed_and_failed() -> None:
    completed = 'data: {"status":"completed","output":[{"role":"assistant","content":[{"type":"text","text":"Done"}]}]}'
    failed = 'data: {"status":"failed","error":{"message":"boom"}}'
    done = parse_sse_data_line(completed)
    fail = parse_sse_data_line(failed)
    assert done is not None
    assert done.status == QwenPawStreamStatus.COMPLETED
    assert fail is not None
    assert fail.status == QwenPawStreamStatus.FAILED
    assert fail.error_message == "boom"
