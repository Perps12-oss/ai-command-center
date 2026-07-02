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
    UI_COMMAND,
    UI_OPEN_CHAT,
)
from ai_command_center.services.command_router_service import CommandRouterService


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

    def test_command_router_forwards_workspace_entity(self) -> None:
        bus = EventBus()
        router = CommandRouterService(bus)
        router.load()
        routed: list[dict] = []

        def capture(event) -> None:
            if event.topic == COMMAND_ROUTED and event.source == "command_router":
                routed.append(dict(event.payload))

        bus.subscribe(COMMAND_ROUTED, capture)
        bus.publish(
            UI_COMMAND,
            {
                "text": "Summarize this card",
                "workspace_entity_id": "card-9",
                "workspace_entity_type": "card",
                "workspace_entity_title": "Sprint",
            },
            source="tests",
        )
        router.unload()
        self.assertEqual(1, len(routed))
        args = routed[0].get("args") or {}
        self.assertEqual("card-9", args.get("workspace_entity_id"))
        self.assertEqual("card", args.get("workspace_entity_type"))
        self.assertEqual("Sprint", args.get("workspace_entity_title"))


if __name__ == "__main__":
    unittest.main()
