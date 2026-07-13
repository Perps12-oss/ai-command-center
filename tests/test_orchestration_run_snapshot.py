"""Tests for OrchestrationRunSnapshot Phase 10 hardening.

Verifies:
1. execution_facts is immutable tuple[tuple[str, str], ...]
2. Run history is maintained
3. provider_health is unified into snapshot
4. Backward compatibility with to_dict()
"""

import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ORCHESTRATION_RUN_SNAPSHOT,
    ORCHESTRATION_PROVIDER_HEALTH,
)
from ai_command_center.domain.orchestration_run_snapshot import (
    OrchestrationRunSnapshot,
    OrchestrationRunEntry,
    _dict_to_immutable,
    _immutable_to_dict,
)


class TestOrchestrationRunSnapshotImmutability(unittest.TestCase):
    """Test that execution_facts is immutable."""

    def test_execution_facts_is_tuple(self):
        """execution_facts should be tuple[tuple[str, str], ...]"""
        snap = OrchestrationRunSnapshot(
            request_id="test-1",
            execution_facts=(("key", "value"),),
        )
        self.assertIsInstance(snap.execution_facts, tuple)
        self.assertEqual(snap.execution_facts, (("key", "value"),))

    def test_execution_facts_immutable(self):
        """execution_facts should not be mutable."""
        snap = OrchestrationRunSnapshot(
            request_id="test-1",
            execution_facts=(("key", "value"),),
        )
        with self.assertRaises(Exception):  # FrozenInstanceError
            snap.execution_facts = (("x", "y"),)

    def test_dict_to_immutable_converts_correctly(self):
        """_dict_to_immutable should convert dict to tuple."""
        d = {"a": "1", "b": "2"}
        result = _dict_to_immutable(d)
        self.assertIsInstance(result, tuple)
        self.assertIn(("a", "1"), result)
        self.assertIn(("b", "2"), result)

    def test_immutable_to_dict_roundtrip(self):
        """_immutable_to_dict should convert back to dict."""
        original = {"a": "1", "b": "2"}
        immutable = _dict_to_immutable(original)
        restored = _immutable_to_dict(immutable)
        self.assertEqual(restored, original)

    def test_execution_facts_dict_property(self):
        """execution_facts_dict property should return dict."""
        snap = OrchestrationRunSnapshot(
            request_id="test-1",
            execution_facts=(("key", "value"),),
        )
        self.assertEqual(snap.execution_facts_dict, {"key": "value"})


class TestOrchestrationRunHistory(unittest.TestCase):
    """Test run history tracking."""

    def setUp(self):
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def test_first_run_creates_history(self):
        """First run should create history entry."""
        self.bus.publish(ORCHESTRATION_RUN_SNAPSHOT, {
            "request_id": "run-1",
            "query": "Test",
            "execution_facts": {"key": "value"},
        }, source="test")

        snap = self.store.snapshot
        self.assertEqual(len(snap.orchestration_run.run_history), 1)
        self.assertEqual(snap.orchestration_run.total_runs, 1)
        self.assertEqual(snap.orchestration_run.run_history[0].request_id, "run-1")

    def test_multiple_runs_accumulate(self):
        """Multiple runs should accumulate in history."""
        for i in range(3):
            self.bus.publish(ORCHESTRATION_RUN_SNAPSHOT, {
                "request_id": f"run-{i}",
                "query": f"Test {i}",
            }, source="test")

        snap = self.store.snapshot
        self.assertEqual(len(snap.orchestration_run.run_history), 3)
        self.assertEqual(snap.orchestration_run.total_runs, 3)

    def test_duplicate_request_id_not_added(self):
        """Same request_id should not duplicate history."""
        self.bus.publish(ORCHESTRATION_RUN_SNAPSHOT, {
            "request_id": "run-1",
            "query": "First",
        }, source="test")
        self.bus.publish(ORCHESTRATION_RUN_SNAPSHOT, {
            "request_id": "run-1",  # Same ID
            "query": "Second",
        }, source="test")

        snap = self.store.snapshot
        self.assertEqual(len(snap.orchestration_run.run_history), 1)
        self.assertEqual(snap.orchestration_run.total_runs, 1)

    def test_history_capped_at_50(self):
        """History should be capped at 50 entries."""
        for i in range(60):
            self.bus.publish(ORCHESTRATION_RUN_SNAPSHOT, {
                "request_id": f"run-{i}",
                "query": f"Test {i}",
            }, source="test")

        snap = self.store.snapshot
        self.assertLessEqual(len(snap.orchestration_run.run_history), 50)
        self.assertEqual(snap.orchestration_run.total_runs, 60)

    def test_latest_run_first_in_history(self):
        """Latest run should be first in history tuple."""
        self.bus.publish(ORCHESTRATION_RUN_SNAPSHOT, {
            "request_id": "run-1",
            "query": "First",
        }, source="test")
        self.bus.publish(ORCHESTRATION_RUN_SNAPSHOT, {
            "request_id": "run-2",
            "query": "Second",
        }, source="test")

        snap = self.store.snapshot
        self.assertEqual(snap.orchestration_run.run_history[0].request_id, "run-2")


class TestProviderHealthUnification(unittest.TestCase):
    """Test provider_health unified into snapshot."""

    def setUp(self):
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def test_provider_health_in_snapshot(self):
        """Provider health should be in orchestration_run snapshot."""
        # First publish provider health
        self.bus.publish(ORCHESTRATION_PROVIDER_HEALTH, {
            "provider_id": "openai",
            "healthy": True,
            "detail": "OK",
            "display_name": "OpenAI",
        }, source="test")

        # Then publish orchestration run
        self.bus.publish(ORCHESTRATION_RUN_SNAPSHOT, {
            "request_id": "run-1",
            "query": "Test",
        }, source="test")

        snap = self.store.snapshot
        
        # Provider health should be in orchestration_run
        self.assertGreater(len(snap.orchestration_run.provider_health), 0)
        
        # And also in the flat field (backward compat)
        self.assertGreater(len(snap.provider_health_map), 0)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with to_dict()."""

    def test_to_dict_returns_dict(self):
        """to_dict() should return dict with execution_facts as dict."""
        snap = OrchestrationRunSnapshot(
            request_id="test-1",
            execution_facts=(("key", "value"),),
        )
        d = snap.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIsInstance(d["execution_facts"], dict)
        self.assertEqual(d["execution_facts"], {"key": "value"})

    def test_to_dict_includes_history(self):
        """to_dict() should include run_history."""
        snap = OrchestrationRunSnapshot(
            request_id="test-1",
            run_history=(
                OrchestrationRunEntry(request_id="run-1"),
            ),
            total_runs=1,
        )
        d = snap.to_dict()
        self.assertIn("run_history", d)
        self.assertEqual(len(d["run_history"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
