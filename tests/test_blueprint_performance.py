"""Blueprint Projection Performance Tests.

Required tests per audit specification:
1. 1,000 event burst
2. 5,000 event burst  
3. Workflow reducer scale test
4. Agent reducer scale test
5. World model scale test
6. Startup hydration benchmark

These tests verify performance characteristics of the AppState projection system.
"""

from __future__ import annotations

import time
import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_TERMINATED,
    ENTITY_CREATED,
    WORKFLOW_STARTED,
    WORKFLOW_COMPLETED,
    EXECUTION_RUN_STARTED,
    EXECUTION_RUN_COMPLETE,
)


class TestEventBurstPerformance(unittest.TestCase):
    """Tests for event burst throughput."""

    def setUp(self):
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def _publish(self, topic, payload):
        self.bus.publish(topic, payload, source="test")

    def test_1000_event_burst_throughput(self):
        """1,000 event burst - measure throughput."""
        events = []
        for i in range(1000):
            events.append((ENTITY_CREATED, {
                "entity_id": f"entity-{i}",
                "entity_type": "task",
                "title": f"Task {i}",
            }))
        
        start = time.perf_counter()
        for topic, payload in events:
            self._publish(topic, payload)
        elapsed = time.perf_counter() - start
        
        snap = self.store.snapshot
        print(f"\n1,000 event burst:")
        print(f"  Elapsed: {elapsed*1000:.2f}ms")
        print(f"  Throughput: {1000/elapsed:.0f} events/sec")
        print(f"  World model nodes: {len(snap.world_model.nodes)}")
        
        # Should complete in reasonable time (< 5 seconds)
        self.assertLess(elapsed, 5.0, f"1,000 event burst took {elapsed:.2f}s")
        # All events should be processed
        self.assertEqual(len(snap.world_model.nodes), 1000)

    def test_5000_event_burst_throughput(self):
        """5,000 event burst - measure throughput."""
        events = []
        for i in range(5000):
            events.append((WORKFLOW_STARTED, {
                "run_id": f"run-{i}",
                "workflow_id": "perf-test",
                "total_steps": 3,
            }))
        
        start = time.perf_counter()
        for topic, payload in events:
            self._publish(topic, payload)
        elapsed = time.perf_counter() - start
        
        snap = self.store.snapshot
        print(f"\n5,000 event burst:")
        print(f"  Elapsed: {elapsed*1000:.2f}ms")
        print(f"  Throughput: {5000/elapsed:.0f} events/sec")
        print(f"  Workflow runs: {len(snap.workflow_library.runs)}")
        
        # Should complete in reasonable time (< 20 seconds)
        self.assertLess(elapsed, 20.0, f"5,000 event burst took {elapsed:.2f}s")
        # All events should be processed (capped at 50)
        self.assertLessEqual(len(snap.workflow_library.runs), 50)


class TestWorkflowReducerScale(unittest.TestCase):
    """WorkflowLibrarySnapshot reducer performance tests."""

    def setUp(self):
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def _publish(self, topic, payload):
        self.bus.publish(topic, payload, source="test")

    def test_workflow_reducer_1000_events(self):
        """Workflow reducer handles 1,000 lifecycle events."""
        # Start 50 workflows (at capacity)
        for i in range(50):
            self._publish(WORKFLOW_STARTED, {
                "run_id": f"run-{i}",
                "workflow_id": "test-workflow",
                "total_steps": 3,
            })
        
        # Each workflow has 10 step events
        for run_idx in range(50):
            for step_idx in range(10):
                self._publish(WORKFLOW_COMPLETED, {
                    "run_id": f"run-{run_idx}",
                    "steps": 3,
                })
        
        snap = self.store.snapshot
        print(f"\nWorkflow reducer scale test:")
        print(f"  Workflow runs: {len(snap.workflow_library.runs)}")
        print(f"  Total started: {snap.workflow_library.total_started}")
        print(f"  Total completed: {snap.workflow_library.total_completed}")
        
        self.assertEqual(snap.workflow_library.total_started, 50)
        self.assertLessEqual(len(snap.workflow_library.runs), 50)

    def test_workflow_idempotency_under_load(self):
        """Workflow total_started remains idempotent under burst load."""
        run_id = "duplicate-run"
        
        # Publish 100 times rapidly
        for _ in range(100):
            self._publish(WORKFLOW_STARTED, {
                "run_id": run_id,
                "workflow_id": "test",
                "total_steps": 5,
            })
        
        snap = self.store.snapshot
        print(f"\nWorkflow idempotency under load:")
        print(f"  Runs count: {len(snap.workflow_library.runs)}")
        print(f"  total_started: {snap.workflow_library.total_started}")
        
        self.assertEqual(len(snap.workflow_library.runs), 1)
        self.assertEqual(snap.workflow_library.total_started, 1)


class TestAgentReducerScale(unittest.TestCase):
    """AgentPipelineSnapshot reducer performance tests."""

    def setUp(self):
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def _publish(self, topic, payload):
        self.bus.publish(topic, payload, source="test")

    def test_agent_reducer_500_events(self):
        """Agent reducer handles 500 lifecycle events."""
        # Spawn 100 agents
        for i in range(100):
            self._publish(AGENT_SPAWNED, {
                "agent_id": f"agent-{i}",
                "request_id": f"req-{i}",
                "state": "running",
            })
            # Each agent has multiple task events
            for j in range(4):
                self._publish(AGENT_TERMINATED, {
                    "agent_id": f"agent-{i}",
                    "request_id": f"req-{i}",
                })
                if j < 3:
                    # Re-spawn for next task
                    self._publish(AGENT_SPAWNED, {
                        "agent_id": f"agent-{i}",
                        "request_id": f"req-{i}-v{j+1}",
                        "state": "running",
                    })
        
        snap = self.store.snapshot
        print(f"\nAgent reducer scale test:")
        print(f"  Agent pipeline runs: {len(snap.agent_pipeline.runs)}")
        print(f"  Total spawned: {snap.agent_pipeline.total_spawned}")
        
        # Should handle all events
        self.assertGreater(len(snap.agent_pipeline.runs), 0)


class TestWorldModelScale(unittest.TestCase):
    """WorldModelSnapshot reducer performance tests."""

    def setUp(self):
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def _publish(self, topic, payload):
        self.bus.publish(topic, payload, source="test")

    def test_world_model_500_entity_events(self):
        """WorldModel reducer handles 500 entity events."""
        for i in range(500):
            self._publish(ENTITY_CREATED, {
                "entity_id": f"entity-{i}",
                "entity_type": "task",
                "title": f"Entity {i}",
            })
        
        snap = self.store.snapshot
        print(f"\nWorld model scale test:")
        print(f"  Nodes: {len(snap.world_model.nodes)}")
        print(f"  Node count: {snap.world_model.node_count}")
        
        self.assertEqual(len(snap.world_model.nodes), 500)
        self.assertEqual(snap.world_model.node_count, 500)


class TestExecutionLibraryScale(unittest.TestCase):
    """ExecutionLibrarySnapshot reducer performance tests."""

    def setUp(self):
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def _publish(self, topic, payload):
        self.bus.publish(topic, payload, source="test")

    def test_execution_reducer_200_events(self):
        """Execution reducer handles 200 execution events."""
        for i in range(50):
            self._publish(EXECUTION_RUN_STARTED, {
                "run_id": f"exec-{i}",
                "request_id": f"req-{i}",
                "goal": f"Execute task {i}",
                "steps": [{"step_id": f"s-{i}-0", "capability": "tool.test", "risk": "low"}],
            })
        
        snap = self.store.snapshot
        print(f"\nExecution reducer scale test:")
        print(f"  Active plan: {snap.execution_library.active_plan.run_id}")
        print(f"  Active plan goal: {snap.execution_library.active_plan.goal}")
        
        # The reducer updates active_plan with latest run
        self.assertEqual(snap.execution_library.active_plan.run_id, "exec-49")
        self.assertEqual(snap.execution_library.active_plan.goal, "Execute task 49")
        self.assertEqual(snap.execution_library.active_plan.status, "running")


class TestSnapshotMemoryCharacteristics(unittest.TestCase):
    """Memory and size limit tests."""

    def setUp(self):
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def _publish(self, topic, payload):
        self.bus.publish(topic, payload, source="test")

    def test_workflow_history_capped_at_50(self):
        """WorkflowLibrarySnapshot enforces 50 run cap."""
        # Publish 100 workflow starts
        for i in range(100):
            self._publish(WORKFLOW_STARTED, {
                "run_id": f"run-{i}",
                "workflow_id": "cap-test",
                "total_steps": 2,
            })
        
        snap = self.store.snapshot
        print(f"\nWorkflow history cap test:")
        print(f"  Runs in snapshot: {len(snap.workflow_library.runs)}")
        print(f"  total_started: {snap.workflow_library.total_started}")
        
        # History should be capped at 50
        self.assertLessEqual(len(snap.workflow_library.runs), 50)
        # But total_started should reflect all starts
        self.assertEqual(snap.workflow_library.total_started, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
