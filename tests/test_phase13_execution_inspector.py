"""Phase 13 - ExecutionInspectorSnapshot projection tests."""

from __future__ import annotations

import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_EVENT_APPENDED,
    EXECUTION_QUERY_RESULT,
    PLAN_GENERATED,
    NOTES_INDEXED,
    UI_EXECUTION_TIMELINE_SCRUB,
)
from ai_command_center.domain.execution_event import ExecutionEvent
from ai_command_center.domain.execution_inspector_snapshot import (
    ExecutionInspectorSnapshot,
)


def _event(index: int, *, request_id: str = "req-1") -> ExecutionEvent:
    return ExecutionEvent(
        event_id=f"evt-{index}",
        trace_id=f"trace-{index // 10}",
        parent_event_id=f"evt-{index - 1}" if index else None,
        timestamp=float(index),
        event_type=f"event.{index}",
        actor="chat",
        scope="execution",
        request_id=request_id,
        payload=(("index", str(index)), ("kind", "demo")),
    )


class TestExecutionInspectorSnapshot(unittest.TestCase):
    def test_defaults(self) -> None:
        snap = ExecutionInspectorSnapshot()
        self.assertEqual(snap.revision, 0)
        self.assertEqual(snap.execution_context.request_id, "")
        self.assertEqual(snap.execution_scrubber.request_id, "")
        self.assertEqual(snap.execution_timeline.events, ())
        self.assertEqual(snap.recent_execution_events, ())
        self.assertEqual(snap.planner_last_plan.plan_id, "")


class TestExecutionInspectorSnapshotReducer(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self) -> None:
        self.store.close()

    def _pub(self, topic: str, payload: dict) -> None:
        self.bus.publish(topic, payload, source="test")

    def test_query_result_projects_context_and_scrubber(self) -> None:
        first = _event(1, request_id="req-9")
        second = _event(2, request_id="req-9")
        self._pub(
            EXECUTION_QUERY_RESULT,
            {
                "request_id": "req-9",
                "provider_id": "ollama",
                "model": "llama3",
                "timeline_source": "events",
                "execution_events": [first.to_bus_payload(), second.to_bus_payload()],
                "trace_spans": [
                    {
                        "span_id": "span-1",
                        "name": "root",
                        "kind": "execution",
                        "status": "ok",
                    }
                ],
            },
        )
        snap = self.store.snapshot.execution_inspector
        self.assertEqual(snap.execution_context.request_id, "req-9")
        self.assertEqual(snap.execution_context.provider_id, "ollama")
        self.assertEqual(snap.execution_scrubber.request_id, "req-9")
        self.assertEqual(len(snap.execution_scrubber.events), 2)
        self.assertEqual(snap.execution_scrubber.source, "events")
        self.assertEqual(snap.execution_timeline.events, ())

    def test_plan_generated_projects_typed_plan(self) -> None:
        plan = {
            "plan_id": "plan-1",
            "goal": "test",
            "steps": [{"step_id": "step-1", "description": "one"}],
        }
        self._pub(PLAN_GENERATED, {"plan": plan})
        snap = self.store.snapshot.execution_inspector
        self.assertEqual(snap.planner_last_plan.plan_id, "plan-1")
        self.assertEqual(len(snap.planner_last_plan.steps), 1)

    def test_execution_event_appended_updates_recent_events_and_timeline(self) -> None:
        self._pub(
            EXECUTION_EVENT_APPENDED,
            _event(1, request_id="req-1").to_bus_payload(),
        )
        snap = self.store.snapshot.execution_inspector
        self.assertEqual(len(snap.recent_execution_events), 1)
        self.assertEqual(snap.recent_execution_events[0].event_id, "evt-1")
        self.assertEqual(len(snap.execution_timeline.events), 1)
        self.assertEqual(snap.execution_timeline.events[0].event_id, "evt-1")

    def test_recent_events_capped(self) -> None:
        for i in range(120):
            self._pub(EXECUTION_EVENT_APPENDED, _event(i).to_bus_payload())
        snap = self.store.snapshot.execution_inspector
        self.assertEqual(len(snap.recent_execution_events), 100)

    def test_scrub_updates_revision(self) -> None:
        self._pub(
            EXECUTION_QUERY_RESULT,
            {
                "request_id": "req-5",
                "execution_events": [
                    _event(1, request_id="req-5").to_bus_payload(),
                    _event(2, request_id="req-5").to_bus_payload(),
                ],
            },
        )
        before = self.store.snapshot.execution_inspector.revision
        self._pub(UI_EXECUTION_TIMELINE_SCRUB, {"request_id": "req-5", "index": 0})
        snap = self.store.snapshot.execution_inspector
        self.assertEqual(snap.execution_scrubber.scrub_index, 0)
        self.assertGreater(snap.revision, before)

    def test_non_target_topic_no_change(self) -> None:
        initial = self.store.snapshot.execution_inspector
        self._pub(NOTES_INDEXED, {})
        after = self.store.snapshot.execution_inspector
        self.assertIs(after, initial)


if __name__ == "__main__":
    unittest.main()
