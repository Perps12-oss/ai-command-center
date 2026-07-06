"""Program 3 Phase 3 — workspace context layer assembly."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.capability_context_assembler import CapabilityContextAssembler
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.entity.entity import (
    ENTITY_TYPE_CARD,
    ENTITY_TYPE_RESOURCE,
    ENTITY_TYPE_WORKSPACE,
)
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    CONTEXT_COMPLETE,
    CONTEXT_SNAPSHOT_CREATED,
    ENTITY_CONTEXT_REQUEST,
    ENTITY_CONTEXT_RESULT,
    LLM_REQUEST,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    UI_COMMAND,
    UI_SELECT_ENTITY,
    WORKSPACE_ACTIVE,
    WORKSPACE_CONTEXT_REQUEST,
    WORKSPACE_CONTEXT_RESULT,
)
from ai_command_center.core.relationship.relationship import RelationshipType
from ai_command_center.core.relationship.relationship_repository import RelationshipRepository
from ai_command_center.core.relationship.relationship_service import RelationshipService
from ai_command_center.core.workspace.workspace_service import WorkspaceService
from ai_command_center.db.connection import connect, init_database
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.ui.controller import UIController


def _stack(bus: EventBus):
    db = init_database(connect(Path(":memory:")))
    entity_service = EntityService(EntityRepository(db), bus)
    relationship_service = RelationshipService(RelationshipRepository(db), bus)
    workspace_service = WorkspaceService(entity_service, bus)
    register_entity_bus_handlers(
        bus,
        entity_service=entity_service,
        relationship_service=relationship_service,
        workspace_service=workspace_service,
        timeline_service=MagicMock(),
        action_registry=MagicMock(),
    )
    return db, entity_service, relationship_service, workspace_service


def _wire_lookup_stubs(bus: EventBus) -> None:
    def _memory(event) -> None:
        bus.publish(
            MEMORY_LOOKUP_RESULT,
            {"request_id": event.payload["request_id"], "snippets": []},
            source="tests",
        )

    def _session(event) -> None:
        bus.publish(
            SESSION_HISTORY_RESULT,
            {"request_id": event.payload["request_id"], "history": []},
            source="tests",
        )

    bus.subscribe(MEMORY_LOOKUP_REQUEST, _memory)
    bus.subscribe(SESSION_HISTORY_REQUEST, _session)


class Phase3WorkspaceContextHandlerTests(unittest.TestCase):
    def test_workspace_context_request_aggregates_workspace_and_graph(self) -> None:
        bus = EventBus()
        db, entity_service, relationship_service, workspace_service = _stack(bus)
        try:
            workspace = workspace_service.create(title="Product")
            card = entity_service.create(
                entity_type=ENTITY_TYPE_CARD,
                title="Roadmap",
                metadata={"workspace_id": str(workspace.id)},
            )
            workspace_service.add_entity(workspace.id, card.id)
            resource = entity_service.create(
                entity_type=ENTITY_TYPE_RESOURCE,
                title="Spec",
                metadata={"resource_type": "url", "url": "https://example.com"},
            )
            relationship_service.create(
                source_id=card.id,
                target_id=resource.id,
                relationship_type=RelationshipType.CONTAINS,
            )

            results: list[dict] = []

            def capture(event) -> None:
                results.append(dict(event.payload))

            bus.subscribe(WORKSPACE_CONTEXT_RESULT, capture)
            bus.publish(
                WORKSPACE_CONTEXT_REQUEST,
                {
                    "request_id": "ws-ctx-1",
                    "workspace_id": str(workspace.id),
                    "entity_id": str(card.id),
                    "max_depth": 2,
                },
                source="tests",
            )
            self.assertEqual(1, len(results))
            snippets = results[0].get("snippets", [])
            joined = "\n".join(str(s) for s in snippets)
            self.assertIn("Active workspace: Product", joined)
            self.assertIn("Roadmap", joined)
            self.assertIn("Relationship graph", joined)
            self.assertIn("Spec", joined)
        finally:
            db.close()


class Phase3AssemblerTests(unittest.TestCase):
    def test_assembler_publishes_workspace_context_request(self) -> None:
        bus = EventBus()
        _wire_lookup_stubs(bus)
        workspace_requests: list[dict] = []
        bus.subscribe(
            WORKSPACE_CONTEXT_REQUEST,
            lambda e: workspace_requests.append(dict(e.payload)),
        )
        assembler = CapabilityContextAssembler(bus, ContextManager())
        assembler.assemble_for_command(
            request_id="req-ws-ctx",
            query="summarize workspace",
            event_payload={"workspace_id": "ws-abc"},
            args={},
            source="tests",
            include_model_resolve=False,
        )
        self.assertEqual(1, len(workspace_requests))
        self.assertEqual("ws-abc", workspace_requests[0].get("workspace_id"))

    def test_assembler_defaults_entity_from_selected_entity(self) -> None:
        bus = EventBus()
        _wire_lookup_stubs(bus)
        entity_requests: list[dict] = []

        def on_entity(event) -> None:
            entity_requests.append(dict(event.payload))
            bus.publish(
                ENTITY_CONTEXT_RESULT,
                {
                    "request_id": event.payload["request_id"],
                    "snippets": ["Selected card context"],
                },
                source="tests",
            )

        bus.subscribe(ENTITY_CONTEXT_REQUEST, on_entity)
        bus.subscribe(
            WORKSPACE_CONTEXT_REQUEST,
            lambda e: bus.publish(
                WORKSPACE_CONTEXT_RESULT,
                {
                    "request_id": e.payload["request_id"],
                    "snippets": ["Workspace layer"],
                },
                source="tests",
            ),
        )

        assembler = CapabilityContextAssembler(bus, ContextManager())
        assembled = assembler.assemble_for_command(
            request_id="req-selected",
            query="plan sprint",
            event_payload={
                "workspace_id": "ws-1",
                "selected_entity_id": "card-9",
                "selected_entity_type": ENTITY_TYPE_CARD,
                "selected_entity_title": "Sprint",
            },
            args={},
            source="tests",
            include_model_resolve=False,
        )
        self.assertTrue(entity_requests)
        self.assertEqual("card-9", entity_requests[0].get("entity_id"))
        self.assertIn("Workspace layer", assembled.bundle.prompt)
        self.assertIn("Selected card context", assembled.bundle.prompt)


class Phase3ChatIntegrationTests(unittest.TestCase):
    def test_chat_handler_projects_workspace_context_bundle(self) -> None:
        bus = EventBus()
        db, entity_service, relationship_service, workspace_service = _stack(bus)
        try:
            workspace = workspace_service.create(title="Ops")
            card = entity_service.create(
                entity_type=ENTITY_TYPE_CARD,
                title="Runbook",
                metadata={"workspace_id": str(workspace.id)},
            )
            workspace_service.add_entity(workspace.id, card.id)
            store = AppStateStore(bus)
            controller = UIController(bus, store, MagicMock())
            router = CommandRouterService(bus)
            chat = ChatHandlerService(bus, ContextManager())
            router.load()
            chat.load()

            snapshots: list[dict] = []
            completes: list[dict] = []
            llm_requests: list[dict] = []
            bus.subscribe(CONTEXT_SNAPSHOT_CREATED, lambda e: snapshots.append(dict(e.payload)))
            bus.subscribe(CONTEXT_COMPLETE, lambda e: completes.append(dict(e.payload)))
            bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))

            bus.publish(
                UI_SELECT_ENTITY,
                {
                    "entity_id": str(card.id),
                    "entity_type": ENTITY_TYPE_CARD,
                    "title": card.title,
                    "workspace_id": str(workspace.id),
                },
                source="tests",
            )
            controller.publish_command("status check")

            router.unload()
            chat.unload()

            self.assertTrue(snapshots)
            snippets = snapshots[0].get("workspace_context_snippets", [])
            self.assertTrue(snippets)
            self.assertEqual(str(workspace.id), snapshots[0].get("workspace_id"))
            self.assertTrue(completes)
            self.assertTrue(llm_requests)
            prompt = str(llm_requests[0].get("bundle", object()).prompt)
            self.assertIn("Runbook", prompt)
        finally:
            db.close()

    def test_command_routed_carries_selected_entity_scope(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        controller = UIController(bus, store, MagicMock())
        router = CommandRouterService(bus)
        router.load()
        routed: list[dict] = []

        def capture_routed(event) -> None:
            if event.source == "command_router":
                routed.append(dict(event.payload))

        bus.subscribe(COMMAND_ROUTED, capture_routed)
        ws_id = "ws-phase3"
        bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": ws_id, "title": "Phase3"},
            source="tests",
        )
        bus.publish(
            UI_SELECT_ENTITY,
            {
                "entity_id": "ent-55",
                "entity_type": ENTITY_TYPE_CARD,
                "title": "Canvas",
            },
            source="tests",
        )
        controller.publish_command("hello workspace")
        router.unload()
        self.assertEqual(1, len(routed))
        self.assertEqual("ent-55", routed[0].get("selected_entity_id"))
        self.assertEqual(INTENT_CHAT, routed[0].get("intent"))


if __name__ == "__main__":
    unittest.main()
