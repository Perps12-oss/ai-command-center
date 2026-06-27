import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CHAT_STARTED,
    COMMAND_ROUTED,
    CONTEXT_SNAPSHOT_CREATED,
)


class ChatWorkspaceV15StateTests(unittest.TestCase):
    def test_chat_lifecycle_projection(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(CHAT_STARTED, {"request_id": "r1"}, source="tests")
        snap = store.snapshot
        self.assertEqual("r1", snap.active_chat_request_id)
        self.assertEqual("streaming", snap.chat_status)
        self.assertTrue(snap.chat_streaming)

        # Stale completion should not replace active request state.
        bus.publish(CHAT_COMPLETE, {"request_id": "stale", "text": "old"}, source="tests")
        self.assertEqual("r1", store.snapshot.active_chat_request_id)

        bus.publish(CHAT_COMPLETE, {"request_id": "r1", "text": "done"}, source="tests")
        snap = store.snapshot
        self.assertEqual("", snap.active_chat_request_id)
        self.assertEqual("complete", snap.chat_status)
        self.assertFalse(snap.chat_streaming)
        self.assertEqual("done", snap.last_assistant_message)

    def test_context_snapshot_projection(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(
            CONTEXT_SNAPSHOT_CREATED,
            {"sources": ["query", "notes", "history"], "context_size_tokens": 321},
            source="tests",
        )
        snap = store.snapshot
        self.assertEqual(("query", "notes", "history"), snap.chat_context_sources)
        self.assertEqual(321, snap.chat_token_estimate)

    def test_history_cancel_error_projection(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(CHAT_HISTORY_LOADED, {"messages": [{"role": "user"}, {"role": "assistant"}]}, source="tests")
        self.assertEqual(2, store.snapshot.chat_history_count)

        bus.publish(CHAT_STARTED, {"request_id": "r2"}, source="tests")
        bus.publish(CHAT_CANCELLED, {"request_id": "r2"}, source="tests")
        self.assertEqual("cancelled", store.snapshot.chat_status)

        bus.publish(CHAT_STARTED, {"request_id": "r3"}, source="tests")
        bus.publish(CHAT_ERROR, {"request_id": "r3", "message": "boom"}, source="tests")
        snap = store.snapshot
        self.assertEqual("error", snap.chat_status)
        self.assertEqual("boom", snap.last_chat_error)

    def test_terminal_events_without_active_request_are_ignored(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(CHAT_COMPLETE, {"request_id": "r-missing", "text": "late"}, source="tests")
        bus.publish(CHAT_CANCELLED, {"request_id": "r-missing"}, source="tests")
        bus.publish(CHAT_ERROR, {"request_id": "r-missing", "message": "late error"}, source="tests")

        snap = store.snapshot
        self.assertEqual("", snap.active_chat_request_id)
        self.assertEqual("idle", snap.chat_status)
        self.assertFalse(snap.chat_streaming)

    def test_duplicate_chat_started_event_is_idempotent(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(CHAT_STARTED, {"request_id": "r4"}, source="tests")
        first = store.snapshot
        bus.publish(CHAT_STARTED, {"request_id": "r4"}, source="tests")
        second = store.snapshot

        self.assertEqual("r4", second.active_chat_request_id)
        self.assertEqual("streaming", second.chat_status)
        self.assertTrue(second.chat_streaming)
        self.assertEqual(first.last_event_topic, second.last_event_topic)

    def test_stale_chat_error_ignored(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(CHAT_STARTED, {"request_id": "r-active"}, source="tests")
        bus.publish(CHAT_ERROR, {"request_id": "r-stale", "message": "stale"}, source="tests")

        snap = store.snapshot
        self.assertEqual("r-active", snap.active_chat_request_id)
        self.assertEqual("streaming", snap.chat_status)
        self.assertFalse(snap.last_chat_error)

    def test_chat_start_projection_from_command_and_start(self) -> None:
        """UI can render a new chat start from AppState alone: last_command + active_chat_request_id."""
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(
            COMMAND_ROUTED,
            {"text": "hello world", "intent": "chat", "args": {"prompt": "hello world"}},
            source="command_router",
        )
        snap = store.snapshot
        self.assertEqual("hello world", snap.last_command)
        self.assertEqual("chat", snap.last_command_intent)

        bus.publish(CHAT_STARTED, {"request_id": "r5"}, source="chat_handler")
        snap = store.snapshot
        self.assertEqual("r5", snap.active_chat_request_id)
        self.assertEqual("streaming", snap.chat_status)
        self.assertTrue(snap.chat_streaming)
        # The user prompt remains available as the source of the user message bubble.
        self.assertEqual("hello world", snap.last_command)


if __name__ == "__main__":
    unittest.main()
