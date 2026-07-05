"""Program 3 W2 — domain re-homing tests."""

from __future__ import annotations

import sqlite3
import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.contracts import (
    TOOL_CONTRACT_VERSION,
    build_workspace_context,
    is_valid_workspace_context,
)
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CHAT_HISTORY_LOADED,
    COMMAND_ROUTED,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MEMORY_REMEMBER,
    MEMORY_STORED,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    NOTES_INDEXED,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    TOOL_FAILED,
    TOOL_INVOKE,
    UI_COMMAND,
    UI_OPEN_CHAT,
    LLM_REQUEST,
)
from ai_command_center.repositories.conversation_repository import (
    ConversationRepository,
    entity_conversation_id,
)
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
)
from ai_command_center.repositories.memory_repository import MemoryRepository
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.services.memory_graph_service import MemoryGraphService
from ai_command_center.services.session_service import SessionService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


class W2SessionScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        DatabaseBootstrapRepository().apply(self.conn)
        self.repo = ConversationRepository(self.conn)
        self.service = SessionService(self.bus, self.repo)
        self.service.load()
        self.history: list[dict] = []
        self.bus.subscribe(
            CHAT_HISTORY_LOADED,
            lambda e: self.history.append(dict(e.payload)),
        )

    def tearDown(self) -> None:
        self.service.unload()
        self.conn.close()

    def test_chat_history_request_uses_workspace_entity_conversation(self) -> None:
        cid = entity_conversation_id("card", "card-w2")
        self.repo.ensure_conversation(cid)
        self.repo.append_message("user", "Scoped hello", conversation_id=cid)

        results: list[dict] = []

        def on_result(event) -> None:
            if event.topic == SESSION_HISTORY_RESULT:
                results.append(dict(event.payload))

        self.bus.subscribe(SESSION_HISTORY_RESULT, on_result)
        self.bus.publish(
            SESSION_HISTORY_REQUEST,
            {
                "request_id": "req-1",
                "workspace_entity_id": "card-w2",
                "workspace_entity_type": "card",
                "workspace_entity_title": "W2 Card",
            },
            source="chat_handler",
        )
        self.assertEqual(1, len(results))
        self.assertEqual(cid, results[0]["conversation_id"])
        self.assertEqual(1, len(results[0]["history"]))
        self.assertEqual("Scoped hello", results[0]["history"][0][1])

    def test_active_entity_from_ui_open_chat_is_default_scope(self) -> None:
        self.bus.publish(
            UI_OPEN_CHAT,
            {"entity_id": "card-active", "entity_type": "card", "title": "Active"},
            source="tests",
        )
        cid = entity_conversation_id("card", "card-active")
        self.repo.append_message("user", "From active entity", conversation_id=cid)

        results: list[dict] = []

        def on_result(event) -> None:
            if event.topic == SESSION_HISTORY_RESULT:
                results.append(dict(event.payload))

        self.bus.subscribe(SESSION_HISTORY_RESULT, on_result)
        self.bus.publish(SESSION_HISTORY_REQUEST, {"request_id": "req-2"}, source="tests")
        self.assertEqual(cid, results[0]["conversation_id"])
        self.assertEqual("From active entity", results[0]["history"][0][1])


class W2MemoryNamespaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        DatabaseBootstrapRepository().apply(self.conn)
        self.repo = MemoryRepository(self.conn)
        self.service = MemoryGraphService(self.bus, self.repo)
        self.service.load()

    def tearDown(self) -> None:
        self.service.unload()
        self.conn.close()

    def test_remember_and_search_respect_workspace_id(self) -> None:
        self.bus.publish(
            MEMORY_REMEMBER,
            {"label": "global", "content": "shared secret", "workspace_id": ""},
            source="tests",
        )
        self.bus.publish(
            MEMORY_REMEMBER,
            {"label": "scoped", "content": "ws-only secret", "workspace_id": "ws-a"},
            source="tests",
        )
        global_hits = self.repo.search("secret", workspace_id="")
        ws_hits = self.repo.search("secret", workspace_id="ws-a")
        self.assertEqual(2, len(global_hits))
        self.assertEqual(1, len(ws_hits))
        self.assertEqual("scoped", ws_hits[0].label)

    def test_command_router_forwards_workspace_id_to_memory_intent(self) -> None:
        router = CommandRouterService(self.bus)
        router.load()
        stored: list[dict] = []
        self.bus.subscribe(MEMORY_STORED, lambda e: stored.append(dict(e.payload)))
        self.bus.publish(
            UI_COMMAND,
            {"text": "remember: api | sk-test", "workspace_id": "ws-mem"},
            source="tests",
        )
        router.unload()
        self.assertEqual(1, len(stored))
        rows = self.repo.search("api", workspace_id="ws-mem")
        self.assertEqual(1, len(rows))
        self.assertEqual(0, len(self.repo.search("api", workspace_id="ws-other")))

    def test_memory_lookup_request_filters_by_workspace_id(self) -> None:
        self.repo.remember(label="k1", content="alpha", workspace_id="ws-1")
        self.repo.remember(label="k2", content="alpha", workspace_id="ws-2")
        results: list[dict] = []

        def on_result(event) -> None:
            if event.topic == MEMORY_LOOKUP_RESULT:
                results.append(dict(event.payload))

        self.bus.subscribe(MEMORY_LOOKUP_RESULT, on_result)
        self.bus.publish(
            MEMORY_LOOKUP_REQUEST,
            {"request_id": "m1", "query": "alpha", "workspace_id": "ws-1"},
            source="tests",
        )
        self.assertEqual(1, len(results))
        self.assertIn("k1", results[0]["snippets"][0])


class W2NotesAsEntitiesTests(unittest.TestCase):
    def test_notes_indexed_projects_note_entities_on_canvas(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        bus.publish(
            NOTES_INDEXED,
            {
                "notes": [
                    {
                        "entity_id": "docs/guide.md",
                        "entity_type": "note",
                        "title": "Guide",
                        "path": "docs/guide.md",
                    },
                    {
                        "entity_id": "todo.md",
                        "entity_type": "note",
                        "title": "Todo",
                        "path": "todo.md",
                    },
                ]
            },
            source="obsidian",
        )
        snap = store.snapshot
        note_entities = [e for e in snap.workspace_os.entities if e.entity_type == "note"]
        self.assertEqual(2, len(note_entities))
        titles = {e.title for e in note_entities}
        self.assertEqual({"Guide", "Todo"}, titles)


class W2ToolContextContractTests(unittest.TestCase):
    def test_workspace_context_helper(self) -> None:
        ctx = build_workspace_context(workspace_id="ws-1", entity_id="card-1", entity_type="card")
        self.assertTrue(is_valid_workspace_context(ctx))
        self.assertFalse(is_valid_workspace_context({}))
        self.assertFalse(is_valid_workspace_context(None))

    def test_non_user_tool_invoke_requires_workspace_context(self) -> None:
        bus = EventBus()
        failed: list[dict] = []
        bus.subscribe(TOOL_FAILED, lambda e: failed.append(dict(e.payload)))
        service = ToolExecutorService(bus, ToolRegistry())
        service.load()
        bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": "bad-1",
                "tool": "shell",
                "args": {"command": "echo ok"},
                "actor_type": "agent",
            },
            source="tests",
        )
        service.unload()
        self.assertEqual(1, len(failed))
        self.assertIn("workspace_context", failed[0]["message"])

    def test_user_shell_invoke_does_not_require_workspace_context(self) -> None:
        bus = EventBus()
        failed: list[dict] = []
        bus.subscribe(TOOL_FAILED, lambda e: failed.append(dict(e.payload)))
        service = ToolExecutorService(bus, ToolRegistry())
        service.load()
        bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": "user-1",
                "tool": "shell",
                "args": {"command": "echo ok"},
                "actor_type": "user",
            },
            source="shell_tool",
        )
        service.unload()
        missing_ctx = [f for f in failed if "workspace_context" in str(f.get("message", ""))]
        self.assertEqual([], missing_ctx)


class W2ChatHandlerSessionScopeTests(unittest.TestCase):
    def test_chat_handler_passes_entity_scope_to_session_history(self) -> None:
        bus = EventBus()
        session_requests: list[dict] = []

        def on_session(event) -> None:
            if event.topic == SESSION_HISTORY_REQUEST:
                session_requests.append(dict(event.payload))
                bus.publish(
                    SESSION_HISTORY_RESULT,
                    {"request_id": event.payload["request_id"], "history": []},
                    source="tests",
                )

        def on_model(event) -> None:
            if event.topic == MODEL_RESOLVE_REQUEST:
                bus.publish(
                    MODEL_RESOLVE_RESULT,
                    {
                        "request_id": event.payload["request_id"],
                        "model": "llama3.2:3b",
                        "provider": "ollama",
                    },
                    source="tests",
                )

        bus.subscribe(SESSION_HISTORY_REQUEST, on_session)
        bus.subscribe(MODEL_RESOLVE_REQUEST, on_model)
        bus.subscribe(
            MEMORY_LOOKUP_REQUEST,
            lambda e: bus.publish(
                MEMORY_LOOKUP_RESULT,
                {"request_id": e.payload["request_id"], "snippets": []},
                source="tests",
            ),
        )
        bus.subscribe(LLM_REQUEST, lambda _e: None)

        handler = ChatHandlerService(bus, ContextManager(max_context_tokens=4096))
        handler.load()
        bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "args": {"prompt": "hello"},
                "workspace_entity_id": "card-99",
                "workspace_entity_type": "card",
                "workspace_entity_title": "Ninety-Nine",
            },
            source="command_router",
        )
        handler.unload()
        self.assertEqual(1, len(session_requests))
        self.assertEqual("card-99", session_requests[0].get("workspace_entity_id"))
        self.assertEqual("card", session_requests[0].get("workspace_entity_type"))


if __name__ == "__main__":
    unittest.main()
