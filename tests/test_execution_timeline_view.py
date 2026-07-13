from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _root = tk.Tk()
    _root.withdraw()
    _root.destroy()
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

from ai_command_center.core.state.execution_state import ExecutionContext, SpanItem
from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.ui.components.inspector.execution_inspector import ExecutionInspector
from ai_command_center.ui.views.execution_timeline_view import ExecutionTimelineView


def _event(index: int, request_id: str) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=f"evt-{index}",
        trace_id="trace-1",
        parent_event_id=None if index == 0 else f"evt-{index - 1}",
        timestamp=float(index),
        event_type=f"event.{index}",
        actor="chat",
        scope="execution",
        request_id=request_id,
        payload=(("index", str(index)), ("request", request_id)),
    )


def test_execution_timeline_view_and_inspector_smoke() -> None:
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:
        pytest.skip(f"tkinter display unavailable: {exc}")
    try:
        events = (_event(0, "req-a"), _event(1, "req-b"), _event(2, "req-a"))

        view = ExecutionTimelineView(root)
        view.pack(fill="both", expand=True)
        view.apply_state(events)
        root.update_idletasks()
        assert view._count_label.cget("text") == "3 events"
        assert len(view._events_list.winfo_children()) == 3

        inspector = ExecutionInspector(root)
        inspector.pack(fill="both", expand=True)
        inspector.update_context(
            ExecutionContext(
                request_id="req-a",
                provider_id="provider-1",
                status="ready",
                trace_spans=(SpanItem(span_id="span-1", name="trace", kind="orchestration"),),
                metrics={"receipt_id": "receipt-1"},
            )
        )
        inspector.update_timeline(events)
        root.update_idletasks()

        assert inspector.timeline_section._title_label.cget("text") == "Timeline (2)"
        assert len(inspector._timeline_list.winfo_children()) == 2
    finally:
        root.destroy()
