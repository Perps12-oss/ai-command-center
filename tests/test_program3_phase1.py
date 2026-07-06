"""Program 3 Phase 1 — workspace-aware chat (active workspace scope)."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.entity.entity import ENTITY_TYPE_WORKSPACE
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MEMORY_REMEMBER,
    MEMORY_STORED,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    UI_COMMAND,
    UI_SELECT_WORKSPACE,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.workspace.workspace_service import WorkspaceService
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.conversation_repository import (
    ConversationRepository,
    entity_conversation_id,
)
from ai_command_center.repositories.memory_repository import MemoryRepository
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.services.memory_graph_service import MemoryGraphService
from ai_command_center.services.session_service import SessionService
from ai_command_center.ui.controller import UIController


def _minimal_stack(bus: EventBus):
    db = init_database(connect(Path(":memory:")))
    entity_service = EntityService(EntityRepository(db), bus)
    workspace_service = WorkspaceService(entity_service, bus)
    register_entity_bus_handlers(
        bus,
        entity_service=entity_service,
        relationship_service=MagicMock(),
        workspace_service=workspace_service,
        timeline_service=MagicMock(),
        action_registry=MagicMock(),
    )
    return db, entity_service, workspace_service


class Phase1ActivateAppStateTests(unittest.TestCase):
    def test_activate_publishes_workspace_active_and_updates_appstate(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        db, entity_service, workspace_service = _minimal_stack(bus)
        try:
            workspace = entity_service.create(
                entity_type=ENTITY_TYPE_WORKSPACE,
                title="Alpha",
            )
            workspace_service.activate(workspace.id)
            snap = store.snapshot
            self.assertEqual(str(workspace.id), snap.active_workspace_id)
            self.assertEqual("Alpha", snap.active_workspace_title)
        finally:
            db.close()

    def test_ui_select_workspace_wires_activate(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        db, entity_service, _workspace_service = _minimal_stack(bus)
        try:
            workspace = entity_service.create(
                entity_type=ENTITY_TYPE_WORKSPACE,
                title="Via UI",
            )
            bus.publish(
                UI_SELECT_WORKSPACE,
                {"workspace_id": str(workspace.id)},
                source="tests",
            )
            self.assertEqual(str(workspace.id), store.snapshot.active_workspace_id)
        finally:
            db.close()


class Phase1CommandRoutingTests(unittest.TestCase):
    def test_command_routed_defaults_workspace_id_from_active_workspace(self) -> None:
        bus = EventBus()
        router = CommandRouterService(bus)
        router.load()
        routed: list[dict] = []

        def capture(event) -> None:
            if event.topic == COMMAND_ROUTED and event.source == "command_router":
                routed.append(dict(event.payload))

        bus.subscribe(COMMAND_ROUTED, capture)
        ws_id = uuid4().hex
        bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": ws_id, "title": "Scoped"},
            source="tests",
        )
        bus.publish(UI_COMMAND, {"text": "hello"}, source="tests")
        router.unload()
        self.assertEqual(1, len(routed))
        payload = routed[0]
        self.assertEqual(INTENT_CHAT, payload.get("intent"))
        self.assertEqual(ws_id, payload.get("workspace_id"))
        args = payload.get("args") or {}
        self.assertEqual(ws_id, args.get("workspace_id"))

    def test_ui_controller_scope_includes_active_workspace_without_chat_entity(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        controller = UIController(bus, store, MagicMock())
        ws_id = uuid4().hex
        bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": ws_id, "title": "Main"},
            source="tests",
        )
        scope = controller.current_workspace_scope()
        self.assertEqual(ws_id, scope.get("workspace_id"))
        self.assertEqual("Main", scope.get("active_workspace_title"))


class Phase1MemorySessionScopeTests(unittest.TestCase):
    def test_memory_remember_defaults_workspace_id_when_active(self) -> None:
        bus = EventBus()
        db = init_database(connect(Path(":memory:")))
        try:
            mem_repo = MemoryRepository(db)
            mem_svc = MemoryGraphService(bus, mem_repo)
            mem_svc.load()
            ws_id = uuid4().hex
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": ws_id, "title": "Mem"},
                source="tests",
            )
            stored: list[dict] = []
            bus.subscribe(MEMORY_STORED, lambda e: stored.append(dict(e.payload)))
            bus.publish(
                MEMORY_REMEMBER,
                {"label": "fact", "content": "scoped value"},
                source="tests",
            )
            mem_svc.unload()
            self.assertEqual(1, len(stored))
            nodes = mem_repo.search("scoped", workspace_id=ws_id)
            self.assertEqual(1, len(nodes))
            self.assertEqual(0, len(mem_repo.search("scoped", workspace_id=uuid4().hex)))
        finally:
            db.close()

    def test_session_history_request_includes_workspace_scope_from_active(self) -> None:
        bus = EventBus()
        db = init_database(connect(Path(":memory:")))
        try:
            conv_repo = ConversationRepository(db)
            session_svc = SessionService(bus, conv_repo)
            session_svc.load()
            ws_id = uuid4().hex
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": ws_id, "title": "Sess"},
                source="tests",
            )
            history_requests: list[dict] = []
            lookup_requests: list[dict] = []

            def on_session_req(event) -> None:
                history_requests.append(dict(event.payload))

            def on_session_result_stub(event) -> None:
                pass

            def on_memory_req(event) -> None:
                lookup_requests.append(dict(event.payload))
                bus.publish(
                    MEMORY_LOOKUP_RESULT,
                    {"request_id": event.payload.get("request_id", ""), "snippets": []},
                    source="tests",
                )

            bus.subscribe(SESSION_HISTORY_REQUEST, on_session_req)
            bus.subscribe(SESSION_HISTORY_RESULT, on_session_result_stub)
            bus.subscribe(MEMORY_LOOKUP_REQUEST, on_memory_req)
            assembler = ContextManager(max_context_tokens=1024)
            from ai_command_center.core.capability_context_assembler import (
                CapabilityContextAssembler,
            )

            cca = CapabilityContextAssembler(bus, assembler)
            cca.assemble_for_command(
                request_id="req-1",
                query="hi",
                event_payload={"workspace_id": ws_id},
                args={},
                source="tests",
                include_model_resolve=False,
            )
            session_svc.unload()
            self.assertTrue(history_requests)
            self.assertEqual(ws_id, history_requests[0].get("workspace_id"))
            self.assertTrue(lookup_requests)
            self.assertEqual(ws_id, lookup_requests[0].get("workspace_id"))
            expected_cid = entity_conversation_id("workspace", ws_id)
            self.assertEqual(expected_cid, session_svc._active_conversation_id)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
