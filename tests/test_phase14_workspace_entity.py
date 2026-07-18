"""Phase 14 - WorkspaceEntitySnapshot projection tests."""

from __future__ import annotations

import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ENTITY_CREATED,
    CHAT_STARTED,
    UI_INSPECT_SELECT,
    UI_SELECT_ENTITY,
    WORKSPACE_ACTIVE,
)
from ai_command_center.domain.workspace_entity_snapshot import WorkspaceEntitySnapshot
from ai_command_center.ui.controller import UIController


class TestWorkspaceEntitySnapshot(unittest.TestCase):
    def test_defaults(self) -> None:
        snap = WorkspaceEntitySnapshot()
        self.assertEqual(snap.revision, 0)
        self.assertEqual(snap.active_workspace_id, "")
        self.assertEqual(snap.selected_entity_id, "")
        self.assertEqual(snap.workspace_entities, ())
        self.assertFalse(snap.inspector.selected)


class TestWorkspaceEntitySnapshotReducer(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self) -> None:
        self.store.close()

    def _pub(self, topic: str, payload: dict) -> None:
        self.bus.publish(topic, payload, source="test")

    def test_workspace_and_selection_projected(self) -> None:
        self._pub(WORKSPACE_ACTIVE, {"workspace_id": "ws-1", "title": "Alpha"})
        self._pub(
            ENTITY_CREATED,
            {
                "entity_id": "card-1",
                "entity_type": "card",
                "title": "Card One",
                "metadata": {"workspace_id": "ws-1"},
            },
        )
        self._pub(
            UI_SELECT_ENTITY,
            {"entity_id": "card-1", "entity_type": "card", "title": "Card One"},
        )
        snap = self.store.snapshot.workspace_entity
        self.assertEqual(snap.active_workspace_id, "ws-1")
        self.assertEqual(snap.active_workspace_title, "Alpha")
        self.assertEqual(snap.selected_entity_id, "card-1")
        self.assertEqual(snap.selected_entity_type, "card")
        self.assertEqual(snap.selected_entity_title, "Card One")
        self.assertEqual(len(snap.workspace_entities), 1)
        self.assertEqual(snap.workspace_entities[0].entity_id, "card-1")

    def test_inspector_selection_included(self) -> None:
        self._pub(
            UI_INSPECT_SELECT,
            {"kind": "message", "ref_id": "msg-1", "label": "hello"},
        )
        snap = self.store.snapshot.workspace_entity
        self.assertIsNotNone(snap.inspector.selected)
        self.assertEqual(snap.inspector.selected.ref_id, "msg-1")

    def test_non_target_topic_no_change(self) -> None:
        initial = self.store.snapshot.workspace_entity
        self._pub(CHAT_STARTED, {"request_id": "chat-1"})
        self.assertIs(self.store.snapshot.workspace_entity, initial)


class TestUIControllerWorkspaceScope(unittest.TestCase):
    def test_current_workspace_scope_uses_consolidated_snapshot(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        controller = UIController(bus, store, lambda: None)
        try:
            bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-2", "title": "Beta"}, source="test")
            bus.publish(
                ENTITY_CREATED,
                {
                    "entity_id": "card-2",
                    "entity_type": "card",
                    "title": "Card Two",
                    "metadata": {"workspace_id": "ws-2"},
                },
                source="test",
            )
            bus.publish(
                UI_SELECT_ENTITY,
                {"entity_id": "card-2", "entity_type": "card", "title": "Card Two"},
                source="test",
            )
            scope = controller.current_workspace_scope()
            self.assertEqual(scope["workspace_id"], "ws-2")
            self.assertEqual(scope["active_workspace_title"], "Beta")
            self.assertEqual(scope["workspace_entity_id"], "card-2")
            self.assertEqual(scope["selected_entity_title"], "Card Two")
        finally:
            controller.close()
            store.close()


if __name__ == "__main__":
    unittest.main()
