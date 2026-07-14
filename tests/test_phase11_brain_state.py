"""Phase 11 - BrainStateSnapshot projection tests."""
from __future__ import annotations

import os
import unittest
from dataclasses import FrozenInstanceError
os.environ.setdefault("APPDATA", "/tmp/aicc_test_appdata")

from ai_command_center.domain.brain_state_snapshot import (
    BrainStateSnapshot, GoalSnapshot, ObservationSnapshot,
    RuntimeActionSnapshot, PlanSnapshot,
    _MAX_GOAL_HISTORY, _MAX_OBSERVATION_HISTORY, _MAX_ACTION_HISTORY,
)


class TestGoalSnapshot(unittest.TestCase):
    def test_defaults(self):
        g = GoalSnapshot()
        self.assertEqual(g.goal_id, "")
        self.assertEqual(g.status, "pending")
        self.assertEqual(g.meta, ())

    def test_from_dict_basic(self):
        g = GoalSnapshot.from_dict({"goal_id": "g1", "text": "do it", "status": "active"})
        self.assertEqual(g.goal_id, "g1")
        self.assertEqual(g.text, "do it")
        self.assertEqual(g.status, "active")

    def test_from_dict_alt_keys(self):
        g = GoalSnapshot.from_dict({"id": "g2", "goal": "alt"})
        self.assertEqual(g.goal_id, "g2")
        self.assertEqual(g.text, "alt")

    def test_from_dict_meta(self):
        g = GoalSnapshot.from_dict({"goal_id": "g3", "meta": {"a": "1", "b": "2"}})
        self.assertIn(("a", "1"), g.meta)

    def test_frozen(self):
        g = GoalSnapshot()
        with self.assertRaises(FrozenInstanceError):
            g.goal_id = "x"  # type: ignore[misc]


class TestObservationSnapshot(unittest.TestCase):
    def test_defaults(self):
        o = ObservationSnapshot()
        self.assertAlmostEqual(o.confidence, 1.0)

    def test_from_dict(self):
        o = ObservationSnapshot.from_dict(
            {"observation_id": "o1", "content": "sky blue", "source": "env", "confidence": 0.9}
        )
        self.assertEqual(o.observation_id, "o1")
        self.assertAlmostEqual(o.confidence, 0.9)


class TestRuntimeActionSnapshot(unittest.TestCase):
    def test_defaults(self):
        a = RuntimeActionSnapshot()
        self.assertEqual(a.status, "started")

    def test_from_dict(self):
        a = RuntimeActionSnapshot.from_dict(
            {"action_id": "a1", "action_type": "shell", "status": "completed", "result": "ok"}
        )
        self.assertEqual(a.action_id, "a1")
        self.assertEqual(a.status, "completed")


class TestPlanSnapshot(unittest.TestCase):
    def test_empty_steps(self):
        p = PlanSnapshot.from_dict({"plan_id": "p1", "goal": "win", "steps": []})
        self.assertEqual(p.steps, ())

    def test_with_steps(self):
        raw = {
            "plan_id": "p2", "goal": "succeed",
            "steps": [
                {"step_id": "s1", "description": "step one", "status": "done"},
                {"step_id": "s2", "description": "step two"},
            ],
        }
        p = PlanSnapshot.from_dict(raw)
        self.assertEqual(len(p.steps), 2)
        self.assertEqual(p.steps[0].status, "done")
        self.assertEqual(p.steps[1].status, "pending")


class TestBrainStateSnapshot(unittest.TestCase):
    def test_defaults(self):
        b = BrainStateSnapshot()
        self.assertEqual(b.kernel_state, "boot")
        self.assertEqual(b.revision, 0)

    def test_with_kernel_state(self):
        b = BrainStateSnapshot()
        b2 = b.with_kernel_state("running")
        self.assertEqual(b2.kernel_state, "running")
        self.assertEqual(b2.revision, 1)
        self.assertEqual(b.kernel_state, "boot")  # original immutable

    def test_with_goal_prepends(self):
        b = BrainStateSnapshot()
        b = b.with_goal(GoalSnapshot(goal_id="g1"))
        b = b.with_goal(GoalSnapshot(goal_id="g2"))
        self.assertEqual(b.recent_goals[0].goal_id, "g2")
        self.assertEqual(b.recent_goals[1].goal_id, "g1")

    def test_goal_history_cap(self):
        b = BrainStateSnapshot()
        for i in range(_MAX_GOAL_HISTORY + 5):
            b = b.with_goal(GoalSnapshot(goal_id=str(i)))
        self.assertEqual(len(b.recent_goals), _MAX_GOAL_HISTORY)

    def test_observation_history_cap(self):
        b = BrainStateSnapshot()
        for i in range(_MAX_OBSERVATION_HISTORY + 5):
            b = b.with_observation(ObservationSnapshot(observation_id=str(i)))
        self.assertEqual(len(b.recent_observations), _MAX_OBSERVATION_HISTORY)

    def test_action_history_cap(self):
        b = BrainStateSnapshot()
        for i in range(_MAX_ACTION_HISTORY + 5):
            b = b.with_action(RuntimeActionSnapshot(action_id=str(i)))
        self.assertEqual(len(b.recent_runtime_actions), _MAX_ACTION_HISTORY)

    def test_revision_increments_per_mutation(self):
        b = BrainStateSnapshot()
        b = b.with_kernel_state("a")
        b = b.with_goal(GoalSnapshot())
        b = b.with_observation(ObservationSnapshot())
        b = b.with_action(RuntimeActionSnapshot())
        b = b.with_plan(PlanSnapshot())
        self.assertEqual(b.revision, 5)


class TestBrainStateSnapshotReducer(unittest.TestCase):
    def setUp(self):
        from ai_command_center.core.app_state import AppStateStore
        from ai_command_center.core.event_bus import EventBus
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def _pub(self, topic, payload=None):
        self.bus.publish(topic, payload or {}, source="test")

    def test_kernel_state_changed(self):
        from ai_command_center.core.events.topics import KERNEL_STATE_CHANGED
        self._pub(KERNEL_STATE_CHANGED, {"to": "running"})
        self.assertEqual(self.store.snapshot.brain_state.kernel_state, "running")
        self.assertEqual(self.store.snapshot.brain_state.revision, 1)

    def test_goal_submitted(self):
        from ai_command_center.core.events.topics import GOAL_SUBMITTED
        self._pub(GOAL_SUBMITTED, {"goal_id": "g1", "text": "do a thing"})
        bs = self.store.snapshot.brain_state
        self.assertGreaterEqual(len(bs.recent_goals), 1)
        self.assertEqual(bs.recent_goals[0].goal_id, "g1")

    def test_goal_completed(self):
        from ai_command_center.core.events.topics import GOAL_COMPLETED
        self._pub(GOAL_COMPLETED, {"goal_id": "g2", "status": "completed"})
        self.assertEqual(self.store.snapshot.brain_state.recent_goals[0].goal_id, "g2")

    def test_observation_received(self):
        from ai_command_center.core.events.topics import OBSERVATION_RECEIVED
        self._pub(OBSERVATION_RECEIVED, {"observation_id": "o1", "content": "sky"})
        self.assertEqual(self.store.snapshot.brain_state.recent_observations[0].observation_id, "o1")

    def test_runtime_action_started(self):
        from ai_command_center.core.events.topics import RUNTIME_ACTION_STARTED
        self._pub(RUNTIME_ACTION_STARTED, {"action_id": "a1", "action_type": "shell"})
        self.assertEqual(self.store.snapshot.brain_state.recent_runtime_actions[0].action_id, "a1")

    def test_plan_generated(self):
        from ai_command_center.core.events.topics import PLAN_GENERATED
        plan_raw = {"plan_id": "p1", "goal": "execute", "steps": [{"step_id": "s1", "description": "go"}]}
        self._pub(PLAN_GENERATED, {"plan": plan_raw})
        bs = self.store.snapshot.brain_state
        self.assertEqual(bs.last_plan.plan_id, "p1")
        self.assertEqual(len(bs.last_plan.steps), 1)

    def test_non_brain_topic_no_change(self):
        from ai_command_center.core.events.topics import NOTES_INDEXED
        initial = self.store.snapshot.brain_state
        self._pub(NOTES_INDEXED, {})
        self.assertIs(self.store.snapshot.brain_state, initial)

    def test_revision_increments_across_events(self):
        from ai_command_center.core.events.topics import (
            GOAL_SUBMITTED, KERNEL_STATE_CHANGED, OBSERVATION_RECEIVED,
        )
        self._pub(KERNEL_STATE_CHANGED, {"to": "running"})
        self._pub(GOAL_SUBMITTED, {"goal_id": "g1"})
        self._pub(OBSERVATION_RECEIVED, {"observation_id": "o1"})
        self.assertEqual(self.store.snapshot.brain_state.revision, 3)


if __name__ == "__main__":
    unittest.main()
