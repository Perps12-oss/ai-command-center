"""Track 3.2 — verify AppStateStore projects feature catalogs from EventBus events."""

from __future__ import annotations

import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ENTITY_CREATED,
    MEMORY_STORED,
    NOTE_CREATED,
    NOTE_INDEX_COMPLETE,
    NOTE_SEARCH_RESULTS,
    NOTE_SELECTED,
    PLUGIN_CATALOG,
    PLUGIN_STATE_CHANGED,
    SYSTEM_SNAPSHOT,
)


class AppStateProjectionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self) -> None:
        self.store.close()

    def _publish(self, topic, payload):
        self.bus.publish(topic, payload, source="test")

    def test_system_snapshot_projected(self):
        self._publish(
            SYSTEM_SNAPSHOT,
            {
                "cpu_percent": 12.3,
                "ram_percent": 45.6,
                "ollama_online": True,
                "health": "healthy",
                "service_states": [("ollama", "ready")],
            },
        )
        snap = self.store.snapshot
        self.assertEqual(snap.system_snapshot.cpu_percent, 12.3)
        self.assertEqual(snap.system_snapshot.ram_percent, 45.6)
        self.assertTrue(snap.system_snapshot.ollama_online)

    def test_notes_catalog_projected_from_search_results(self):
        self._publish(
            NOTE_SEARCH_RESULTS,
            {
                "query": "api",
                "results": [
                    {"path": "notes/api.md", "title": "API", "snippet": "rest api"},
                    {"path": "notes/auth.md", "title": "Auth", "snippet": "oauth"},
                ],
            },
        )
        snap = self.store.snapshot
        self.assertEqual(len(snap.notes_catalog), 2)
        self.assertEqual(snap.notes_catalog[0].title, "API")

    def test_note_selected_and_created_projected(self):
        self._publish(
            NOTE_SELECTED,
            {"path": "notes/api.md", "title": "API", "body": "body text"},
        )
        self.assertEqual(self.store.snapshot.note_selected.title, "API")
        self.assertEqual(self.store.snapshot.note_selected.snippet, "body text")

        self._publish(NOTE_CREATED, {"path": "notes/new.md", "title": "New"})
        self.assertEqual(self.store.snapshot.notes_catalog[0].path, "notes/new.md")

    def test_note_index_status_projected(self):
        self._publish(NOTE_INDEX_COMPLETE, {"files": 42, "ms": 120})
        self.assertEqual(self.store.snapshot.note_index_status, (42, 120))

    def test_memory_catalog_projected(self):
        self._publish(MEMORY_STORED, {"id": "m1", "label": "api-key"})
        self.assertEqual(self.store.snapshot.memory_catalog[0].label, "api-key")

    def test_plugin_catalog_projected(self):
        self._publish(
            PLUGIN_CATALOG,
            {
                "plugins": [
                    {"id": "chat", "name": "Chat", "enabled": True, "kind": "core"},
                    {"id": "notes", "name": "Notes", "enabled": False, "kind": "extension"},
                ],
            },
        )
        snap = self.store.snapshot
        self.assertEqual(len(snap.plugin_catalog), 2)
        self.assertEqual(snap.plugin_catalog[1].plugin_id, "notes")
        self.assertFalse(snap.plugin_catalog[1].enabled)

        self._publish(PLUGIN_STATE_CHANGED, {"id": "notes", "enabled": True})
        self.assertTrue(self.store.snapshot.plugin_catalog[1].enabled)

    def test_workspace_os_entities_projected(self):
        self._publish(
            ENTITY_CREATED,
            {"entity_id": "e1", "entity_type": "workspace", "title": "Proj"},
        )
        self._publish(
            ENTITY_CREATED,
            {"entity_id": "e2", "entity_type": "card", "title": "Card"},
        )
        snap = self.store.snapshot
        self.assertEqual(snap.workspace_os.entity_count, 2)
        self.assertEqual(len(snap.workspace_os.entities), 2)
        self.assertEqual(snap.workspace_os.entities[0].title, "Proj")


if __name__ == "__main__":
    unittest.main()
