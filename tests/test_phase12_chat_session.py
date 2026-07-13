"""Phase 12 - ChatSessionSnapshot projection tests."""
from __future__ import annotations
import os, unittest
os.environ.setdefault("APPDATA", "/tmp/aicc_test_appdata")

from ai_command_center.domain.chat_session_snapshot import (
    ChatSessionSnapshot, ChatMessageSnapshot, ChatWorkspaceEntityRef, ChatContextInfo,
)


class TestChatMessageSnapshot(unittest.TestCase):
    def test_defaults(self):
        m = ChatMessageSnapshot()
        self.assertEqual(m.role, "")
        self.assertEqual(m.content, "")

    def test_frozen(self):
        m = ChatMessageSnapshot(role="user", content="hi")
        with self.assertRaises((AttributeError, TypeError)):
            object.__setattr__(m, "role", "x")


class TestChatWorkspaceEntityRef(unittest.TestCase):
    def test_is_set_false_by_default(self):
        r = ChatWorkspaceEntityRef()
        self.assertFalse(r.is_set)

    def test_is_set_true_when_entity_id(self):
        r = ChatWorkspaceEntityRef(entity_id="e1", entity_type="card", title="My Card")
        self.assertTrue(r.is_set)


class TestChatContextInfo(unittest.TestCase):
    def test_defaults(self):
        c = ChatContextInfo()
        self.assertEqual(c.sources, ())
        self.assertEqual(c.token_estimate, 0)


class TestChatSessionSnapshot(unittest.TestCase):
    def test_defaults(self):
        s = ChatSessionSnapshot()
        self.assertEqual(s.status, "idle")
        self.assertFalse(s.streaming)
        self.assertEqual(s.revision, 0)
        self.assertEqual(s.session_key, "default")
        self.assertFalse(s.workspace_entity.is_set)

    def test_frozen(self):
        s = ChatSessionSnapshot()
        with self.assertRaises((AttributeError, TypeError)):
            object.__setattr__(s, "status", "streaming")


class TestChatSessionSnapshotReducer(unittest.TestCase):
    def setUp(self):
        from ai_command_center.core.app_state import AppStateStore
        from ai_command_center.core.event_bus import EventBus
        self.bus = EventBus()
        self.store = AppStateStore(self.bus)

    def tearDown(self):
        self.store.close()

    def _pub(self, topic, payload=None):
        self.bus.publish(topic, payload or {}, source="test")

    def test_chat_started_updates_snapshot(self):
        from ai_command_center.core.events.topics import CHAT_STARTED
        self._pub(CHAT_STARTED, {"request_id": "req-1"})
        snap = self.store.snapshot.chat_session
        self.assertEqual(snap.active_request_id, "req-1")
        self.assertEqual(snap.status, "streaming")
        self.assertTrue(snap.streaming)
        self.assertGreater(snap.revision, 0)

    def test_chat_chunk_appends_buffer(self):
        from ai_command_center.core.events.topics import CHAT_STARTED, CHAT_CHUNK
        self._pub(CHAT_STARTED, {"request_id": "req-1"})
        self._pub(CHAT_CHUNK, {"request_id": "req-1", "text": "Hello"})
        self._pub(CHAT_CHUNK, {"request_id": "req-1", "text": " world"})
        snap = self.store.snapshot.chat_session
        self.assertEqual(snap.stream_buffer, "Hello world")

    def test_chat_complete_clears_streaming(self):
        from ai_command_center.core.events.topics import CHAT_STARTED, CHAT_COMPLETE
        self._pub(CHAT_STARTED, {"request_id": "req-2"})
        self._pub(CHAT_COMPLETE, {"request_id": "req-2", "text": "done answer"})
        snap = self.store.snapshot.chat_session
        self.assertEqual(snap.status, "complete")
        self.assertFalse(snap.streaming)
        self.assertEqual(snap.last_assistant_message, "done answer")

    def test_chat_cancelled_status(self):
        from ai_command_center.core.events.topics import CHAT_STARTED, CHAT_CANCELLED
        self._pub(CHAT_STARTED, {"request_id": "req-3"})
        self._pub(CHAT_CANCELLED, {"request_id": "req-3"})
        snap = self.store.snapshot.chat_session
        self.assertEqual(snap.status, "cancelled")
        self.assertFalse(snap.streaming)

    def test_chat_error_captures_message(self):
        from ai_command_center.core.events.topics import CHAT_STARTED, CHAT_ERROR
        self._pub(CHAT_STARTED, {"request_id": "req-4"})
        self._pub(CHAT_ERROR, {"request_id": "req-4", "message": "Timeout"})
        snap = self.store.snapshot.chat_session
        self.assertEqual(snap.status, "error")
        self.assertEqual(snap.last_error, "Timeout")

    def test_chat_history_loaded_populates_messages(self):
        from ai_command_center.core.events.topics import CHAT_HISTORY_LOADED
        self._pub(CHAT_HISTORY_LOADED, {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ]
        })
        snap = self.store.snapshot.chat_session
        self.assertEqual(len(snap.history_messages), 2)
        self.assertEqual(snap.history_messages[0].role, "user")
        self.assertEqual(snap.history_messages[1].content, "hello")

    def test_ui_chat_new_session_resets_entity(self):
        from ai_command_center.core.events.topics import UI_CHAT_NEW_SESSION, UI_OPEN_CHAT
        self._pub(UI_OPEN_CHAT, {"entity_id": "e1", "entity_type": "card", "title": "T"})
        self.assertTrue(self.store.snapshot.chat_session.workspace_entity.is_set)
        self._pub(UI_CHAT_NEW_SESSION, {})
        self.assertFalse(self.store.snapshot.chat_session.workspace_entity.is_set)

    def test_revision_increments_per_chat_event(self):
        from ai_command_center.core.events.topics import CHAT_STARTED, CHAT_CHUNK, CHAT_COMPLETE
        r0 = self.store.snapshot.chat_session.revision
        self._pub(CHAT_STARTED, {"request_id": "req-5"})
        r1 = self.store.snapshot.chat_session.revision
        self._pub(CHAT_CHUNK, {"request_id": "req-5", "text": "x"})
        r2 = self.store.snapshot.chat_session.revision
        self._pub(CHAT_COMPLETE, {"request_id": "req-5", "text": "done"})
        r3 = self.store.snapshot.chat_session.revision
        self.assertGreater(r1, r0)
        self.assertGreater(r2, r1)
        self.assertGreater(r3, r2)

    def test_non_chat_topic_no_change(self):
        from ai_command_center.core.events.topics import NOTES_INDEXED
        initial = self.store.snapshot.chat_session
        self._pub(NOTES_INDEXED, {})
        self.assertIs(self.store.snapshot.chat_session, initial)


if __name__ == "__main__":
    unittest.main()
