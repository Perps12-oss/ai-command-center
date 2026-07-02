"""Track R7 — AppState projections for agent and workflow runs."""

from __future__ import annotations

import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_TASK_COMPLETE,
    AGENT_TASK_REQUEST,
    AGENT_TERMINATED,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)


class AgentWorkflowAppStateProjectionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self) -> None:
        self.store.close()

    def _publish(self, topic: str, payload: dict) -> None:
        self.bus.publish(topic, payload, source="test")

    def test_agent_spawn_projects_run_and_active_id(self) -> None:
        self._publish(
            AGENT_SPAWNED,
            {
                "agent_id": "agent-1",
                "request_id": "req-1",
                "state": "spawning",
                "workspace_id": "ws-1",
            },
        )
        snap = self.store.snapshot
        self.assertEqual(snap.active_agent_run_id, "agent-1")
        self.assertEqual(len(snap.agent_runs), 1)
        self.assertEqual(snap.agent_runs[0].agent_id, "agent-1")
        self.assertEqual(snap.agent_runs[0].state, "spawning")
        self.assertEqual(snap.agent_runs[0].workspace_id, "ws-1")

    def test_agent_task_and_terminate_lifecycle(self) -> None:
        self._publish(
            AGENT_SPAWNED,
            {"agent_id": "a1", "request_id": "r1", "state": "running"},
        )
        self._publish(
            AGENT_TASK_REQUEST,
            {"agent_id": "a1", "request_id": "r1", "task": "do work"},
        )
        self._publish(
            AGENT_TASK_COMPLETE,
            {"agent_id": "a1", "request_id": "r1", "status": "complete"},
        )
        self._publish(
            AGENT_TERMINATED,
            {"agent_id": "a1", "request_id": "r1", "state": "terminated"},
        )
        snap = self.store.snapshot
        self.assertEqual(snap.active_agent_run_id, "")
        self.assertEqual(snap.agent_runs[0].state, "terminated")
        self.assertEqual(snap.agent_runs[0].task, "do work")
        self.assertEqual(snap.agent_runs[0].steps, 1)

    def test_agent_terminate_with_error_marks_failed(self) -> None:
        self._publish(
            AGENT_SPAWNED,
            {"agent_id": "a2", "request_id": "r2", "state": "running"},
        )
        self._publish(
            AGENT_TERMINATED,
            {"agent_id": "a2", "request_id": "r2", "error": "cancelled"},
        )
        self.assertEqual(self.store.snapshot.agent_runs[0].state, "failed")
        self.assertEqual(self.store.snapshot.agent_runs[0].error, "cancelled")

    def test_workflow_started_projects_run_and_active_id(self) -> None:
        self._publish(
            WORKFLOW_STARTED,
            {"run_id": "run-1", "workflow_id": "daily-sync", "total_steps": 3},
        )
        snap = self.store.snapshot
        self.assertEqual(snap.active_workflow_run_id, "run-1")
        self.assertEqual(len(snap.workflow_runs), 1)
        self.assertEqual(snap.workflow_runs[0].workflow_id, "daily-sync")
        self.assertEqual(snap.workflow_runs[0].state, "running")
        self.assertEqual(snap.workflow_runs[0].total_steps, 3)

    def test_workflow_step_progress_and_completion(self) -> None:
        self._publish(
            WORKFLOW_STARTED,
            {"run_id": "run-2", "workflow_id": "wf", "total_steps": 2},
        )
        self._publish(
            WORKFLOW_STEP_STARTED,
            {"run_id": "run-2", "step_id": "s0", "index": 0, "type": "tool"},
        )
        self._publish(
            WORKFLOW_STEP_COMPLETED,
            {"run_id": "run-2", "step_id": "s0", "index": 0, "success": True},
        )
        self._publish(
            WORKFLOW_COMPLETED,
            {"run_id": "run-2", "workflow_id": "wf", "steps": 2},
        )
        snap = self.store.snapshot
        self.assertEqual(snap.active_workflow_run_id, "")
        self.assertEqual(snap.workflow_runs[0].state, "completed")
        self.assertEqual(snap.workflow_runs[0].current_step_index, 1)

    def test_workflow_failed_clears_active_id(self) -> None:
        self._publish(
            WORKFLOW_STARTED,
            {"run_id": "run-3", "workflow_id": "wf", "total_steps": 1},
        )
        self._publish(
            WORKFLOW_FAILED,
            {"run_id": "run-3", "error": "tool step failed"},
        )
        snap = self.store.snapshot
        self.assertEqual(snap.active_workflow_run_id, "")
        self.assertEqual(snap.workflow_runs[0].state, "failed")
        self.assertEqual(snap.workflow_runs[0].error, "tool step failed")


if __name__ == "__main__":
    unittest.main()
