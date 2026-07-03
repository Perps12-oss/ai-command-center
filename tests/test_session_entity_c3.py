"""Per-entity session persistence for SessionService (Track 9 C3)."""

from __future__ import annotations

import sqlite3
import unittest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_HISTORY_LOADED,
    UI_OPEN_CHAT,
)
from ai_command_center.repositories.conversation_repository import (
    ConversationRepository,
    entity_conversation_id,
)
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
)
from ai_command_center.services.session_service import SessionService


class SessionServiceEntityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        DatabaseBootstrapRepository().apply(self.conn)
        self.repo = ConversationRepository(self.conn)
        self.service = SessionService(self.bus, self.repo)
        self.service.load()
        self.history_events: list[dict] = []

        def capture(event) -> None:
            if event.topic == CHAT_HISTORY_LOADED:
                self.history_events.append(dict(event.payload))

        self.bus.subscribe(CHAT_HISTORY_LOADED, capture)

    def tearDown(self) -> None:
        self.service.unload()
        self.conn.close()

    def test_open_chat_switches_conversation_and_restores_history(self) -> None:
        cid_a = entity_conversation_id("card", "card-a")
        self.repo.ensure_conversation(cid_a)
        self.repo.append_message("user", "Hello A", conversation_id=cid_a)
        self.repo.append_message("assistant", "Hi A", conversation_id=cid_a)

        cid_b = entity_conversation_id("card", "card-b")
        self.repo.ensure_conversation(cid_b)
        self.repo.append_message("user", "Hello B", conversation_id=cid_b)

        self.bus.publish(
            UI_OPEN_CHAT,
            {"entity_id": "card-a", "entity_type": "card", "title": "Alpha"},
            source="tests",
        )
        messages_a = self.history_events[-1]["messages"]
        self.assertEqual(2, len(messages_a))
        self.assertEqual("Hello A", messages_a[0]["content"])

        self.bus.publish(
            UI_OPEN_CHAT,
            {"entity_id": "card-b", "entity_type": "card", "title": "Beta"},
            source="tests",
        )
        messages_b = self.history_events[-1]["messages"]
        self.assertEqual(1, len(messages_b))
        self.assertEqual("Hello B", messages_b[0]["content"])
        self.assertEqual(cid_b, self.history_events[-1]["conversation_id"])

        self.bus.publish(UI_OPEN_CHAT, {"entity_id": ""}, source="tests")
        default_messages = self.history_events[-1]["messages"]
        self.assertEqual([], default_messages)


if __name__ == "__main__":
    unittest.main()
