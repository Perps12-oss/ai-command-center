import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_CHUNK,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CHAT_STARTED,
    CONTEXT_SNAPSHOT_CREATED,
    EXECUTION_AUTHORITY_DECISION,
    GOAL_SUBMIT_REQUEST,
    UI_CHAT_NEW_SESSION,
    UI_COMMAND,
    UI_OPEN_CHAT,
)
from ai_command_center.repositories.conversation_repository import entity_conversation_id
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService


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

    def test_chat_chunk_buffer_projection(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(CHAT_STARTED, {"request_id": "r5"}, source="tests")
        bus.publish(CHAT_CHUNK, {"request_id": "r5", "text": "Hel"}, source="tests")
        bus.publish(CHAT_CHUNK, {"request_id": "r5", "text": "lo"}, source="tests")
        snap = store.snapshot
        self.assertEqual("Hello", snap.chat_stream_buffer)
        self.assertEqual(3, snap.chat_stream_revision)

        bus.publish(CHAT_CHUNK, {"request_id": "stale", "text": "ignored"}, source="tests")
        self.assertEqual("Hello", store.snapshot.chat_stream_buffer)

        bus.publish(CHAT_COMPLETE, {"request_id": "r5", "text": "Hello"}, source="tests")
        cleared = store.snapshot
        self.assertEqual("", cleared.chat_stream_buffer)
        self.assertFalse(cleared.chat_streaming)

    def test_pending_user_text_projection(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(
            EXECUTION_AUTHORITY_DECISION,
            {"text": "What is Python?", "capability": "llm"},
            source="execution_authority",
        )
        self.assertEqual("What is Python?", store.snapshot.chat_pending_user_text)

        bus.publish(
            EXECUTION_AUTHORITY_DECISION,
            {"text": "note: daily log", "capability": "notes.create"},
            source="execution_authority",
        )
        self.assertEqual("", store.snapshot.chat_pending_user_text)

        bus.publish(
            EXECUTION_AUTHORITY_DECISION,
            {"text": "Explain async", "capability": "llm"},
            source="execution_authority",
        )
        bus.publish(CHAT_STARTED, {"request_id": "r6"}, source="tests")
        snap = store.snapshot
        self.assertEqual("", snap.chat_pending_user_text)
        self.assertEqual("Explain async", snap.chat_started_user_text)

    def test_history_messages_projection(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(
            CHAT_HISTORY_LOADED,
            {
                "messages": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello"},
                ]
            },
            source="tests",
        )
        snap = store.snapshot
        self.assertEqual(2, snap.chat_history_count)
        self.assertEqual(1, snap.chat_history_revision)
        self.assertEqual("user", snap.chat_history_messages[0].role)
        self.assertEqual("Hi", snap.chat_history_messages[0].content)
        self.assertEqual("assistant", snap.chat_history_messages[1].role)
        self.assertEqual("Hello", snap.chat_history_messages[1].content)

    def test_open_chat_entity_projection(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(
            UI_OPEN_CHAT,
            {"entity_id": "card-1", "entity_type": "card", "title": "Roadmap"},
            source="tests",
        )
        snap = store.snapshot
        self.assertEqual("card-1", snap.chat_workspace_entity_id)
        self.assertEqual("card", snap.chat_workspace_entity_type)
        self.assertEqual("Roadmap", snap.chat_workspace_entity_title)

        bus.publish(UI_OPEN_CHAT, {"entity_id": ""}, source="tests")
        cleared = store.snapshot
        self.assertEqual("", cleared.chat_workspace_entity_id)
        self.assertEqual("", cleared.chat_workspace_entity_type)
        self.assertEqual("", cleared.chat_workspace_entity_title)
        self.assertEqual("default", cleared.chat_active_session_key)

    def test_open_chat_entity_metadata_projection(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(
            UI_OPEN_CHAT,
            {
                "entity_id": "res-1",
                "entity_type": "resource",
                "title": "Docs",
                "description": "API reference",
                "url": "https://example.com/docs",
            },
            source="tests",
        )
        snap = store.snapshot
        self.assertEqual("API reference", snap.chat_workspace_entity_description)
        self.assertEqual("https://example.com/docs", snap.chat_workspace_entity_url)
        self.assertEqual(
            entity_conversation_id("resource", "res-1"),
            snap.chat_active_session_key,
        )

    def test_entity_session_switch_updates_session_key(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(
            UI_OPEN_CHAT,
            {"entity_id": "card-1", "entity_type": "card", "title": "A"},
            source="tests",
        )
        first_key = store.snapshot.chat_active_session_key
        bus.publish(
            UI_OPEN_CHAT,
            {"entity_id": "card-2", "entity_type": "card", "title": "B"},
            source="tests",
        )
        second = store.snapshot
        self.assertNotEqual(first_key, second.chat_active_session_key)
        self.assertEqual("card-2", second.chat_workspace_entity_id)

    def test_new_session_clears_entity_context(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)

        bus.publish(
            UI_OPEN_CHAT,
            {"entity_id": "card-1", "entity_type": "card", "title": "Roadmap"},
            source="tests",
        )
        bus.publish(UI_CHAT_NEW_SESSION, {}, source="tests")
        snap = store.snapshot
        self.assertEqual("", snap.chat_workspace_entity_id)
        self.assertEqual("default", snap.chat_active_session_key)

    def test_execution_authority_forwards_workspace_entity(self) -> None:
        bus = EventBus()
        authority = ExecutionAuthorityService(bus)
        authority.load()
        goals: list[dict] = []
        bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))
        bus.publish(
            UI_COMMAND,
            {
                "text": "Summarize this card",
                "workspace_id": "ws-v15",
                "workspace_entity_id": "card-9",
                "workspace_entity_type": "card",
                "workspace_entity_title": "Sprint",
            },
            source="tests",
        )
        authority.unload()
        self.assertEqual(1, len(goals))
        ctx = goals[0].get("workspace_context") or {}
        self.assertEqual("card-9", ctx.get("entity_id"))
        self.assertEqual("card", ctx.get("entity_type"))

    def test_execution_authority_forwards_workspace_entity_metadata(self) -> None:
        bus = EventBus()
        authority = ExecutionAuthorityService(bus)
        authority.load()
        goals: list[dict] = []
        bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))
        bus.publish(
            UI_COMMAND,
            {
                "text": "Summarize resource",
                "workspace_id": "ws-v15",
                "workspace_entity_id": "res-3",
                "workspace_entity_type": "resource",
                "workspace_entity_title": "Handbook",
                "workspace_entity_description": "Team wiki",
                "workspace_entity_url": "https://wiki.example/handbook",
            },
            source="tests",
        )
        authority.unload()
        self.assertEqual(1, len(goals))
        # Metadata is carried on the authority decision / workspace scope for llm steps.
        decision = goals[0].get("authority_decision") or {}
        self.assertEqual("llm", decision.get("capability"))
        ctx = goals[0].get("workspace_context") or {}
        self.assertEqual("res-3", ctx.get("entity_id"))


if __name__ == "__main__":
    unittest.main()
