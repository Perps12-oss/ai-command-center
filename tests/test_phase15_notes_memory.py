"""Phase 15 - NotesMemorySnapshot projection tests."""

from __future__ import annotations

import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_STARTED,
    MEMORY_SELECTED,
    MEMORY_STORED,
    NOTE_INDEX_COMPLETE,
    NOTE_SEARCH_RESULTS,
    NOTE_SELECTED,
    WORKSPACE_ACTIVE,
)
from ai_command_center.domain.notes_memory_snapshot import NotesMemorySnapshot


class TestNotesMemorySnapshot(unittest.TestCase):
    def test_defaults(self) -> None:
        snap = NotesMemorySnapshot()
        self.assertEqual(snap.revision, 0)
        self.assertEqual(snap.notes_catalog, ())
        self.assertIsNone(snap.note_selected)
        self.assertEqual(snap.note_index_status, ())
        self.assertEqual(snap.memory_catalog, ())
        self.assertEqual(snap.memory_selected, ())


class TestNotesMemorySnapshotReducer(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self) -> None:
        self.store.close()

    def _pub(self, topic: str, payload: dict) -> None:
        self.bus.publish(topic, payload, source="test")

    def test_note_and_memory_state_is_consolidated(self) -> None:
        self._pub(WORKSPACE_ACTIVE, {"workspace_id": "ws-1", "title": "Alpha"})
        self._pub(
            NOTE_SEARCH_RESULTS,
            {
                "query": "api",
                "results": [
                    {"path": "notes/api.md", "title": "API", "snippet": "rest api"},
                ],
            },
        )
        self._pub(
            NOTE_SELECTED,
            {"path": "notes/api.md", "title": "API", "body": "body text"},
        )
        self._pub(NOTE_INDEX_COMPLETE, {"files": 42, "ms": 120})
        self._pub(MEMORY_STORED, {"id": "m1", "label": "api-key", "workspace_id": "ws-1"})
        self._pub(MEMORY_SELECTED, {"labels": ["api-key"]})

        snap = self.store.snapshot.notes_memory
        self.assertGreater(snap.revision, 0)
        self.assertEqual(len(snap.notes_catalog), 1)
        self.assertEqual(snap.notes_catalog[0].path, "notes/api.md")
        self.assertIsNotNone(snap.note_selected)
        self.assertEqual(snap.note_selected.title, "API")
        self.assertEqual(snap.note_index_status, (42, 120))
        self.assertEqual(len(snap.memory_catalog), 1)
        self.assertEqual(snap.memory_catalog[0].label, "api-key")
        self.assertEqual(snap.memory_selected, ("api-key",))

    def test_non_target_topic_no_change(self) -> None:
        initial = self.store.snapshot.notes_memory
        self._pub(CHAT_STARTED, {"request_id": "chat-1"})
        after = self.store.snapshot.notes_memory
        self.assertIs(after, initial)


if __name__ == "__main__":
    unittest.main()
