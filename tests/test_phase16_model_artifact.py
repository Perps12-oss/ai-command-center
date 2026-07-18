"""Phase 16 - ModelArtifactSnapshot projection tests."""

from __future__ import annotations

import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ARTIFACT_CREATED,
    CHAT_STARTED,
    MODEL_SELECTED,
    TOOL_COMPLETED,
    TOOL_STARTED,
)
from ai_command_center.domain.model_artifact_snapshot import ModelArtifactSnapshot


class TestModelArtifactSnapshot(unittest.TestCase):
    def test_defaults(self) -> None:
        snap = ModelArtifactSnapshot()
        self.assertEqual(snap.revision, 0)
        self.assertEqual(snap.model_selection.model, "")
        self.assertEqual(snap.recent_tool_runs, ())
        self.assertEqual(snap.recent_artifacts, ())


class TestModelArtifactSnapshotReducer(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self) -> None:
        self.store.close()

    def _pub(self, topic: str, payload: dict) -> None:
        self.bus.publish(topic, payload, source="test")

    def test_model_tool_and_artifact_state_is_consolidated(self) -> None:
        self._pub(
            MODEL_SELECTED,
            {
                "model": "gpt-4o-mini",
                "provider": "openai",
                "intent": "chat",
                "reason": "test",
                "routing_tier": "default",
                "workspace_id": "ws-1",
            },
        )
        self._pub(TOOL_STARTED, {"invoke_id": "run-1", "tool": "search.notes"})
        self._pub(TOOL_COMPLETED, {"invoke_id": "run-1", "tool": "search.notes"})
        self._pub(
            ARTIFACT_CREATED,
            {
                "artifact_id": "art-1",
                "kind": "markdown",
                "label": "Summary",
                "content": "done",
            },
        )

        snap = self.store.snapshot.model_artifact
        self.assertGreater(snap.revision, 0)
        self.assertEqual(snap.model_selection.model, "gpt-4o-mini")
        self.assertEqual(snap.model_selection.provider, "openai")
        self.assertEqual(len(snap.recent_tool_runs), 1)
        self.assertEqual(snap.recent_tool_runs[0].invoke_id, "run-1")
        self.assertEqual(snap.recent_tool_runs[0].status, "completed")
        self.assertEqual(len(snap.recent_artifacts), 1)
        self.assertEqual(snap.recent_artifacts[0].artifact_id, "art-1")

    def test_non_target_topic_no_change(self) -> None:
        initial = self.store.snapshot.model_artifact
        self._pub(CHAT_STARTED, {"request_id": "chat-1"})
        after = self.store.snapshot.model_artifact
        self.assertIs(after, initial)


if __name__ == "__main__":
    unittest.main()
