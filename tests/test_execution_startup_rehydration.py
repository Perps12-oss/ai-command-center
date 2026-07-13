"""Test Execution Library startup rehydration.

This test verifies that ExecutionRunService publishes EXECUTION_RUNS_LOADED
on startup, which allows AppState.execution_library to be populated without UI interaction.
"""

import unittest
from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import EXECUTION_RUNS_LOADED


class TestExecutionStartupRehydration(unittest.TestCase):
    """Tests for Execution Library startup rehydration."""

    def test_execution_runs_loaded_populates_snapshot(self):
        """AppState.execution_library should be populated after EXECUTION_RUNS_LOADED event."""
        bus = EventBus()
        store = AppStateStore(bus)
        
        # Simulate the startup event that would be published by ExecutionRunService
        bus.publish(EXECUTION_RUNS_LOADED, {
            "runs": [
                {
                    "run_id": "run-1",
                    "request_id": "req-1",
                    "source": "orchestration",
                    "created_at": 1234567890.0,
                    "summary": "Execute task 1",
                },
                {
                    "run_id": "run-2",
                    "request_id": "req-2",
                    "source": "chat",
                    "created_at": 1234567891.0,
                    "summary": "Execute task 2",
                },
            ]
        }, source="execution_run")
        
        # Verify the snapshot is populated
        snap = store.snapshot
        self.assertEqual(len(snap.execution_library.run_history), 2,
            "ExecutionLibrarySnapshot should have 2 runs after startup event")
        self.assertEqual(snap.execution_library.total_runs, 2,
            "total_runs should be 2")
        
        # Verify run IDs
        run_ids = {r.run_id for r in snap.execution_library.run_history}
        self.assertEqual(run_ids, {"run-1", "run-2"})
        
        store.close()

    def test_execution_runs_loaded_idempotent(self):
        """EXECUTTION_RUNS_LOADED should not duplicate runs with same run_id."""
        bus = EventBus()
        store = AppStateStore(bus)
        
        # First load
        bus.publish(EXECUTION_RUNS_LOADED, {
            "runs": [
                {"run_id": "run-1", "request_id": "req-1", "source": "test", "created_at": 1.0, "summary": ""},
            ]
        }, source="execution_run")
        
        # Second load with same run_id - should not duplicate
        bus.publish(EXECUTION_RUNS_LOADED, {
            "runs": [
                {"run_id": "run-1", "request_id": "req-1", "source": "test", "created_at": 1.0, "summary": ""},
                {"run_id": "run-2", "request_id": "req-2", "source": "test", "created_at": 2.0, "summary": ""},
            ]
        }, source="execution_run")
        
        snap = store.snapshot
        self.assertEqual(len(snap.execution_library.run_history), 2,
            "Should have 2 unique runs")
        self.assertEqual(snap.execution_library.total_runs, 2,
            "total_runs should be 2 (1 from first + 1 new from second)")
        
        store.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
