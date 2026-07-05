"""Program 3 W3 — bus-native Workspace OS and entity context tests."""

from __future__ import annotations

import unittest
import uuid
from pathlib import Path
from uuid import UUID

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.entity.entity_context import format_entity_context
from ai_command_center.core.entity.entity import (
    ENTITY_TYPE_CARD,
    ENTITY_TYPE_WORKSPACE,
)
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    ENTITY_CONTEXT_REQUEST,
    ENTITY_CONTEXT_RESULT,
    ENTITY_CREATE_REQUEST,
    ENTITY_CREATE_RESULT,
    ENTITY_CREATED,
    LLM_REQUEST,
    SEARCH_RESULTS,
    UI_CREATE_CARD,
    UI_CREATE_WORKSPACE,
    UI_SEARCH_WORKSPACE_OS,
    WORKSPACE_CREATE_REQUEST,
)
from ai_command_center.core.relationship.relationship import RelationshipType
from ai_command_center.core.relationship.relationship_repository import RelationshipRepository
from ai_command_center.core.relationship.relationship_service import RelationshipService
from ai_command_center.core.workspace.workspace_service import WorkspaceService
from ai_command_center.core.workspace_os_service import WorkspaceOsService
from ai_command_center.db.connection import connect, init_database
from ai_command_center.services.chat_handler_service import ChatHandlerService


def _minimal_wos_stack(bus: EventBus, db_path: str = ":memory:") -> tuple:
    """Build Workspace OS stack with bus handlers (no full app)."""
    db = init_database(connect(Path(db_path)))
    entity_repo = EntityRepository(db)
    rel_repo = RelationshipRepository(db)
    entity_service = EntityService(entity_repo, bus)
    relationship_service = RelationshipService(rel_repo, bus)
    workspace_service = WorkspaceService(entity_service, bus)

    from ai_command_center.core.action.action_registry import ActionRegistry
    from ai_command_center.core.ai.capability_registry_service import (
        AICapabilityRegistryService,
    )
    from ai_command_center.core.feature.feature_registry import FeatureRegistry
    from ai_command_center.core.observability.observability_service import (
        ObservabilityService,
    )
    from ai_command_center.core.permission.permission_service import PermissionService
    from ai_command_center.core.search.command_palette_service import CommandPaletteService
    from ai_command_center.core.search.search_provider import FTSSearchProvider
    from ai_command_center.core.snapshot.snapshot_service import SnapshotService
    from ai_command_center.core.timeline.timeline_repository import TimelineRepository
    from ai_command_center.core.timeline.timeline_service import TimelineService

    action_registry = ActionRegistry(bus)
    timeline_service = TimelineService(TimelineRepository(db), bus)
    permission_service = PermissionService(bus)
    register_entity_bus_handlers(
        bus,
        entity_service=entity_service,
        relationship_service=relationship_service,
        workspace_service=workspace_service,
        timeline_service=timeline_service,
        action_registry=action_registry,
    )
    wos = WorkspaceOsService(
        bus=bus,
        entity_service=entity_service,
        relationship_service=relationship_service,
        workspace_service=workspace_service,
        action_registry=action_registry,
        timeline_service=timeline_service,
        permission_service=permission_service,
        observability_service=ObservabilityService(bus),
        snapshot_service=SnapshotService(db, bus),
        feature_registry=FeatureRegistry(),
        ai_capability_registry_service=AICapabilityRegistryService(permission_service),
        command_palette_service=CommandPaletteService(bus),
        search_provider=FTSSearchProvider(entity_service),
    )
    return wos, entity_service, relationship_service, workspace_service, db


class W3EntityBusHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.wos, self.entity_service, self.relationship_service, self.workspace_service, self.db = (
            _minimal_wos_stack(self.bus)
        )
        self.wos.load()

    def tearDown(self) -> None:
        self.wos.unload()

    def test_entity_create_request_returns_result(self) -> None:
        request_id = uuid.uuid4().hex
        results: list[dict] = []

        def on_result(event) -> None:
            if event.topic == ENTITY_CREATE_RESULT:
                results.append(dict(event.payload))

        self.bus.subscribe(ENTITY_CREATE_RESULT, on_result)
        self.bus.publish(
            ENTITY_CREATE_REQUEST,
            {
                "request_id": request_id,
                "entity_type": ENTITY_TYPE_CARD,
                "title": "Bus Card",
            },
            source="tests",
        )
        self.assertEqual(1, len(results))
        self.assertEqual(request_id, results[0]["request_id"])
        self.assertIn("entity_id", results[0])
        entity = self.entity_service.get(UUID(str(results[0]["entity_id"])))
        self.assertIsNotNone(entity)
        assert entity is not None
        self.assertEqual("Bus Card", entity.title)

    def test_entity_context_request_includes_relationships(self) -> None:
        workspace = self.workspace_service.create(title="Ctx WS")
        card = self.entity_service.create(
            entity_type=ENTITY_TYPE_CARD,
            title="Ctx Card",
        )
        self.relationship_service.create(
            source_id=workspace.id,
            target_id=card.id,
            relationship_type=RelationshipType.CONTAINS,
        )

        request_id = uuid.uuid4().hex
        snippets: list[str] = []

        def on_result(event) -> None:
            if event.topic == ENTITY_CONTEXT_RESULT:
                snippets.extend(event.payload.get("snippets", []))

        self.bus.subscribe(ENTITY_CONTEXT_RESULT, on_result)
        self.bus.publish(
            ENTITY_CONTEXT_REQUEST,
            {"request_id": request_id, "entity_id": str(card.id)},
            source="tests",
        )
        self.assertTrue(snippets)
        combined = "\n".join(snippets)
        self.assertIn("Ctx Card", combined)
        self.assertIn("Related entities", combined)
        self.assertIn("workspace", combined.lower())

    def test_workspace_create_via_bus_request(self) -> None:
        request_id = uuid.uuid4().hex
        self.bus.publish(
            WORKSPACE_CREATE_REQUEST,
            {
                "request_id": request_id,
                "title": "Bus Workspace",
                "description": "via bus",
            },
            source="tests",
        )
        workspaces = self.workspace_service.get_all()
        self.assertEqual(1, len(workspaces))
        self.assertEqual("Bus Workspace", workspaces[0].title)


class W3WorkspaceOsOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.wos, self.entity_service, _, self.workspace_service, _ = _minimal_wos_stack(
            self.bus
        )
        self.wos.load()
        self.created: list[dict] = []
        self.bus.subscribe(
            ENTITY_CREATED,
            lambda e: self.created.append(dict(e.payload)),
        )

    def tearDown(self) -> None:
        self.wos.unload()

    def test_ui_create_workspace_via_orchestrator(self) -> None:
        self.bus.publish(
            UI_CREATE_WORKSPACE,
            {"title": "Orchestrated WS", "description": ""},
            source="tests",
        )
        workspaces = self.workspace_service.get_all()
        self.assertEqual(1, len(workspaces))
        self.assertEqual("Orchestrated WS", workspaces[0].title)

    def test_ui_create_card_flow(self) -> None:
        workspace = self.workspace_service.create(title="Parent WS")
        self.bus.publish(
            UI_CREATE_CARD,
            {
                "workspace_id": str(workspace.id),
                "title": "Orchestrated Card",
                "description": "desc",
            },
            source="tests",
        )
        updated = self.workspace_service.get(workspace.id)
        assert updated is not None
        entity_ids = [UUID(e) for e in updated.metadata.get("entities", [])]
        self.assertEqual(1, len(entity_ids))
        card = self.entity_service.get(entity_ids[0])
        assert card is not None
        self.assertEqual("Orchestrated Card", card.title)

    def test_ui_search_publishes_search_results(self) -> None:
        self.entity_service.create(
            entity_type=ENTITY_TYPE_CARD,
            title="Find Me Unique",
        )
        captured: list[dict] = []
        self.bus.subscribe(
            SEARCH_RESULTS,
            lambda e: captured.append(dict(e.payload)),
        )
        self.bus.publish(
            UI_SEARCH_WORKSPACE_OS,
            {"query": "Find Me Unique"},
            source="tests",
        )
        self.assertEqual(1, len(captured))
        self.assertGreaterEqual(captured[0].get("count", 0), 1)


class W3ChatEntityContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        db = init_database(connect(Path(":memory:")))
        entity_repo = EntityRepository(db)
        rel_repo = RelationshipRepository(db)
        self.entity_service = EntityService(entity_repo, self.bus)
        relationship_service = RelationshipService(rel_repo, self.bus)
        workspace_service = WorkspaceService(self.entity_service, self.bus)
        from ai_command_center.core.action.action_registry import ActionRegistry
        from ai_command_center.core.timeline.timeline_repository import TimelineRepository
        from ai_command_center.core.timeline.timeline_service import TimelineService

        register_entity_bus_handlers(
            self.bus,
            entity_service=self.entity_service,
            relationship_service=relationship_service,
            workspace_service=workspace_service,
            timeline_service=TimelineService(TimelineRepository(db), self.bus),
            action_registry=ActionRegistry(self.bus),
        )
        self.chat = ChatHandlerService(self.bus, ContextManager())
        self.chat.load()
        self.llm_requests: list[dict] = []
        self.bus.subscribe(
            LLM_REQUEST,
            lambda e: self.llm_requests.append(dict(e.payload)),
        )

    def tearDown(self) -> None:
        self.chat.unload()

    def test_chat_uses_entity_context_bus_snippets(self) -> None:
        card = self.entity_service.create(
            entity_type=ENTITY_TYPE_CARD,
            title="Chat Scoped Card",
            description="Entity graph context",
        )
        self.bus.publish(
            COMMAND_ROUTED,
            {
                "intent": INTENT_CHAT,
                "args": {"prompt": "hello from scoped chat"},
                "workspace_entity_id": str(card.id),
            },
            source="command_router",
        )
        self.assertEqual(1, len(self.llm_requests))
        bundle = self.llm_requests[0]["bundle"]
        self.assertIn("Chat Scoped Card", bundle.prompt)
        self.assertIn("Entity graph context", bundle.prompt)


class W3ContextManagerFormatTests(unittest.TestCase):
    def test_format_entity_context(self) -> None:
        text = format_entity_context(
            {
                "entity_id": "abc-123",
                "entity_type": "card",
                "entity_title": "My Card",
                "entity_description": "A note",
                "url": "https://example.com",
            }
        )
        assert text is not None
        self.assertIn("My Card", text)
        self.assertIn("abc-123", text)
        self.assertIn("https://example.com", text)


class W3AppStateEntityTopicTests(unittest.TestCase):
    def test_entity_created_updates_app_state(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        bus.publish(
            ENTITY_CREATED,
            {
                "entity_id": str(uuid.uuid4()),
                "entity_type": ENTITY_TYPE_WORKSPACE,
                "title": "State WS",
            },
            source="tests",
        )
        snapshot = store.snapshot.workspace_os
        self.assertGreaterEqual(snapshot.entity_count, 1)


class W3HandlerErrorResultTests(unittest.TestCase):
    """Bus handlers publish error payloads instead of swallowing exceptions."""

    def test_search_failure_publishes_error_result(self) -> None:
        from unittest.mock import MagicMock

        bus = EventBus()
        entity_service = MagicMock()
        entity_service.search.side_effect = RuntimeError("search failed")
        results: list[dict] = []

        def on_result(event) -> None:
            results.append(dict(event.payload))

        from ai_command_center.core.events.topics import ENTITY_SEARCH_REQUEST, ENTITY_SEARCH_RESULT

        bus.subscribe(ENTITY_SEARCH_RESULT, on_result)
        register_entity_bus_handlers(
            bus,
            entity_service=entity_service,
            relationship_service=MagicMock(),
            workspace_service=MagicMock(),
            timeline_service=MagicMock(),
            action_registry=MagicMock(),
        )
        rid = uuid.uuid4().hex
        bus.publish(
            ENTITY_SEARCH_REQUEST,
            {"request_id": rid, "query": "x"},
            source="tests",
        )
        self.assertEqual(1, len(results))
        self.assertIn("error", results[0])
        self.assertEqual(0, results[0]["count"])

    def test_timeline_failure_publishes_error_result(self) -> None:
        from unittest.mock import MagicMock

        bus = EventBus()
        timeline_service = MagicMock()
        timeline_service.record.side_effect = ValueError("bad entity id")
        results: list[dict] = []

        def on_result(event) -> None:
            results.append(dict(event.payload))

        from ai_command_center.core.events.topics import TIMELINE_RECORD_REQUEST, TIMELINE_RECORD_RESULT

        bus.subscribe(TIMELINE_RECORD_RESULT, on_result)
        register_entity_bus_handlers(
            bus,
            entity_service=MagicMock(),
            relationship_service=MagicMock(),
            workspace_service=MagicMock(),
            timeline_service=timeline_service,
            action_registry=MagicMock(),
        )
        rid = uuid.uuid4().hex
        bus.publish(
            TIMELINE_RECORD_REQUEST,
            {
                "request_id": rid,
                "event_type": "resource.launched",
                "entity_id": "not-a-uuid",
            },
            source="tests",
        )
        self.assertEqual(1, len(results))
        self.assertIn("error", results[0])
        self.assertNotIn("recorded", results[0])


if __name__ == "__main__":
    unittest.main()
