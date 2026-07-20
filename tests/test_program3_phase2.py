"""Program 3 Phase 2 — workspace entities, selection, and scope inheritance."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.entity.entity import (
    ENTITY_TYPE_CARD,
    ENTITY_TYPE_RESOURCE,
    ENTITY_TYPE_WORKSPACE,
)
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.relationship.relationship_service import RelationshipService
from ai_command_center.core.event_bus import (
    EVENT_WORKSPACE_ACTIVATED,
    EVENT_WORKSPACE_CREATED,
    EVENT_WORKSPACE_DEACTIVATED,
    EVENT_WORKSPACE_LAYOUT_CHANGED,
    EventBus,
)
from ai_command_center.core.events.topics import (
    MEMORY_STORED,
    UI_COMMAND,
    UI_OPEN_CHAT,
    UI_SELECT_ENTITY,
    WORKSPACE_ACTIVATED,
    WORKSPACE_CREATED,
    WORKSPACE_DEACTIVATED,
    WORKSPACE_LAYOUT_CHANGED,
)
from ai_command_center.core.relationship.relationship import RelationshipType
from ai_command_center.core.relationship.relationship_repository import (
    RelationshipRepository,
)
from ai_command_center.core.workspace.workspace_service import WorkspaceService
from ai_command_center.db.connection import connect, init_database
from ai_command_center.orchestration.state_capability_tools import bind_state_capability_tools
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.memory_repository import MemoryRepository
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.memory_graph_service import MemoryGraphService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry
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


class Phase2TopicAliasTests(unittest.TestCase):
    def test_legacy_workspace_event_constants_alias_topics(self) -> None:
        self.assertEqual(EVENT_WORKSPACE_CREATED, WORKSPACE_CREATED)
        self.assertEqual(EVENT_WORKSPACE_ACTIVATED, WORKSPACE_ACTIVATED)
        self.assertEqual(EVENT_WORKSPACE_DEACTIVATED, WORKSPACE_DEACTIVATED)
        self.assertEqual(EVENT_WORKSPACE_LAYOUT_CHANGED, WORKSPACE_LAYOUT_CHANGED)


class Phase2SelectionTests(unittest.TestCase):
    def test_select_entity_projects_selected_entity_in_appstate(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        db, entity_service, _, _ = _stack(bus)
        try:
            workspace = entity_service.create(
                entity_type=ENTITY_TYPE_WORKSPACE,
                title="Alpha",
            )
            bus.publish(
                UI_SELECT_ENTITY,
                {
                    "entity_id": str(workspace.id),
                    "entity_type": ENTITY_TYPE_WORKSPACE,
                    "title": workspace.title,
                },
                source="tests",
            )
            snap = store.snapshot
            self.assertEqual(str(workspace.id), snap.selected_entity_id)
            self.assertEqual(ENTITY_TYPE_WORKSPACE, snap.selected_entity_type)
            self.assertEqual("Alpha", snap.selected_entity_title)
            self.assertEqual(str(workspace.id), snap.active_workspace_id)
        finally:
            db.close()

    def test_card_select_activates_parent_workspace(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        db, entity_service, _, workspace_service = _stack(bus)
        try:
            workspace = workspace_service.create(title="Parent")
            card = entity_service.create(
                entity_type=ENTITY_TYPE_CARD,
                title="Roadmap",
                metadata={"workspace_id": str(workspace.id)},
            )
            workspace_service.add_entity(workspace.id, card.id)
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
            snap = store.snapshot
            self.assertEqual(str(card.id), snap.selected_entity_id)
            self.assertEqual(str(workspace.id), snap.active_workspace_id)
        finally:
            db.close()


class Phase2OpenChatScopeTests(unittest.TestCase):
    def test_open_chat_from_card_includes_parent_workspace_id(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        controller = UIController(bus, store, MagicMock())
        captured: list[dict] = []
        bus.subscribe(UI_OPEN_CHAT, lambda e: captured.append(dict(e.payload)))

        ws_id = uuid4().hex
        card_id = uuid4().hex
        controller.publish_open_chat(
            card_id,
            ENTITY_TYPE_CARD,
            "Design",
            workspace_id=ws_id,
        )

        self.assertEqual(1, len(captured))
        self.assertEqual(ws_id, captured[0].get("workspace_id"))
        self.assertEqual(card_id, captured[0].get("entity_id"))

    def test_memory_remember_inherits_workspace_from_active_card_scope(self) -> None:
        bus = EventBus()
        db, entity_service, _, workspace_service = _stack(bus)
        try:
            mem_repo = MemoryRepository(db)
            mem_svc = MemoryGraphService(bus, mem_repo)
            mem_svc.load()
            store = AppStateStore(bus)
            controller = UIController(bus, store, MagicMock())
            workspace = workspace_service.create(title="Scoped WS")
            card = entity_service.create(
                entity_type=ENTITY_TYPE_CARD,
                title="Card",
                metadata={"workspace_id": str(workspace.id)},
            )
            workspace_service.add_entity(workspace.id, card.id)
            ws_id = str(workspace.id)
            card_id = str(card.id)

            bus.publish(
                UI_OPEN_CHAT,
                {
                    "entity_id": card_id,
                    "entity_type": ENTITY_TYPE_CARD,
                    "title": "Card",
                    "workspace_id": ws_id,
                },
                source="tests",
            )
            bus.publish(
                UI_SELECT_ENTITY,
                {
                    "entity_id": card_id,
                    "entity_type": ENTITY_TYPE_CARD,
                    "title": "Card",
                    "workspace_id": ws_id,
                },
                source="tests",
            )

            registry = ToolRegistry()
            bind_state_capability_tools(registry, bus=bus, memory=mem_svc)
            executor = ToolExecutorService(bus, registry)
            scheduler = SingleGoalScheduler(bus, GoalRepository(db))
            orchestrator = ExecutionOrchestratorService(bus)
            authority = ExecutionAuthorityService(bus)
            executor.load()
            scheduler.load()
            orchestrator.load()
            authority.load()

            commands: list[dict] = []
            stored: list[dict] = []
            bus.subscribe(UI_COMMAND, lambda e: commands.append(dict(e.payload)))
            bus.subscribe(MEMORY_STORED, lambda e: stored.append(dict(e.payload)))
            scope = controller.current_workspace_scope()
            controller.publish_memory_remember(
                "fact",
                "scoped from card chat",
                workspace_scope=scope,
            )
            authority.unload()
            orchestrator.unload()
            scheduler.unload()
            executor.unload()
            mem_svc.unload()

            self.assertEqual(ws_id, scope.get("workspace_id"))
            self.assertEqual(1, len(commands))
            self.assertIn("remember:", commands[0].get("text", ""))
            self.assertEqual(ws_id, commands[0].get("workspace_id"))
            self.assertEqual(1, len(stored))
            self.assertEqual(ws_id, stored[0].get("workspace_id"))
            nodes = mem_repo.search("scoped", workspace_id=ws_id)
            self.assertEqual(1, len(nodes))
        finally:
            db.close()

    def test_resource_select_resolves_workspace_via_card_relationship(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        db, entity_service, relationship_service, workspace_service = _stack(bus)
        try:
            workspace = workspace_service.create(title="Ops")
            card = entity_service.create(
                entity_type=ENTITY_TYPE_CARD,
                title="Links",
                metadata={"workspace_id": str(workspace.id)},
            )
            workspace_service.add_entity(workspace.id, card.id)
            resource = entity_service.create(
                entity_type=ENTITY_TYPE_RESOURCE,
                title="Docs",
                metadata={
                    "resource_type": "url",
                    "url": "https://example.com",
                    "card_id": str(card.id),
                },
            )
            relationship_service.create(
                source_id=card.id,
                target_id=resource.id,
                relationship_type=RelationshipType.CONTAINS,
            )
            bus.publish(
                UI_SELECT_ENTITY,
                {
                    "entity_id": str(resource.id),
                    "entity_type": ENTITY_TYPE_RESOURCE,
                    "title": resource.title,
                },
                source="tests",
            )
            snap = store.snapshot
            self.assertEqual(str(resource.id), snap.selected_entity_id)
            self.assertEqual(str(workspace.id), snap.active_workspace_id)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
