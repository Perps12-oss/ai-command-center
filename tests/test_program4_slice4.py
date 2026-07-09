"""Program 4 slice 4 — large context graph depth + plugin canvas entities."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.capability_context_assembler import (
    DEFAULT_GRAPH_MAX_DEPTH,
    CapabilityContextAssembler,
    resolve_graph_max_depth,
)
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.entity.entity import (
    ENTITY_TYPE_CARD,
    ENTITY_TYPE_RESOURCE,
    RESOURCE_TYPE_PLUGIN,
)
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ENTITY_CREATED,
    ENTITY_UPDATED,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    PLUGIN_REGISTERED_ENTITY,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    WORKSPACE_CONTEXT_REQUEST,
)
from ai_command_center.core.relationship.relationship import RelationshipType
from ai_command_center.core.relationship.relationship_repository import RelationshipRepository
from ai_command_center.core.relationship.relationship_service import RelationshipService
from ai_command_center.core.workspace.workspace_service import WorkspaceService
from ai_command_center.db.connection import connect, init_database
from ai_command_center.services.plugin_registry_service import PluginRegistryService


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


class ResolveGraphMaxDepthTests(unittest.TestCase):
    def test_default_depth(self) -> None:
        self.assertEqual(DEFAULT_GRAPH_MAX_DEPTH, 4)
        self.assertEqual(resolve_graph_max_depth({}, {}), 4)

    def test_payload_override_and_clamp(self) -> None:
        self.assertEqual(resolve_graph_max_depth({"max_depth": 6}, {}), 6)
        self.assertEqual(resolve_graph_max_depth({"graph_max_depth": 99}, {}), 8)
        self.assertEqual(resolve_graph_max_depth({"max_depth": 0}, {}), 1)
        self.assertEqual(resolve_graph_max_depth({}, {"max_depth": 3}), 3)


class LargeContextAssemblerTests(unittest.TestCase):
    def test_assembler_publishes_default_graph_depth(self) -> None:
        bus = EventBus()
        _wire_lookup_stubs(bus)
        workspace_requests: list[dict] = []
        bus.subscribe(
            WORKSPACE_CONTEXT_REQUEST,
            lambda e: workspace_requests.append(dict(e.payload)),
        )
        assembler = CapabilityContextAssembler(bus, ContextManager())
        assembler.assemble_for_command(
            request_id="req-depth",
            query="summarize workspace",
            event_payload={"workspace_id": "ws-abc"},
            args={},
            source="tests",
            include_model_resolve=False,
        )
        self.assertEqual(1, len(workspace_requests))
        self.assertEqual(DEFAULT_GRAPH_MAX_DEPTH, workspace_requests[0].get("max_depth"))

    def test_assembler_honors_max_depth_override(self) -> None:
        bus = EventBus()
        _wire_lookup_stubs(bus)
        workspace_requests: list[dict] = []
        bus.subscribe(
            WORKSPACE_CONTEXT_REQUEST,
            lambda e: workspace_requests.append(dict(e.payload)),
        )
        assembler = CapabilityContextAssembler(bus, ContextManager())
        assembler.assemble_for_command(
            request_id="req-depth-2",
            query="deep graph",
            event_payload={"workspace_id": "ws-abc", "max_depth": 5},
            args={},
            source="tests",
            include_model_resolve=False,
        )
        self.assertEqual(5, workspace_requests[0].get("max_depth"))

    def test_workspace_context_traverses_deeper_than_two(self) -> None:
        bus = EventBus()
        db, entity_service, relationship_service, workspace_service = _stack(bus)
        try:
            workspace = workspace_service.create(title="Deep")
            a = entity_service.create(entity_type=ENTITY_TYPE_CARD, title="A")
            b = entity_service.create(entity_type=ENTITY_TYPE_CARD, title="B")
            c = entity_service.create(entity_type=ENTITY_TYPE_CARD, title="C")
            d = entity_service.create(entity_type=ENTITY_TYPE_CARD, title="D")
            workspace_service.add_entity(workspace.id, a.id)
            for src, tgt in ((a, b), (b, c), (c, d)):
                relationship_service.create(
                    source_id=src.id,
                    target_id=tgt.id,
                    relationship_type=RelationshipType.CONTAINS,
                )

            results: list[dict] = []
            bus.subscribe(
                "workspace.context.result",
                lambda e: results.append(dict(e.payload)),
            )
            bus.publish(
                WORKSPACE_CONTEXT_REQUEST,
                {
                    "request_id": "deep-1",
                    "workspace_id": str(workspace.id),
                    "entity_id": str(a.id),
                    "max_depth": 4,
                },
                source="tests",
            )
            self.assertEqual(1, len(results))
            joined = "\n".join(str(s) for s in results[0].get("snippets", []))
            self.assertIn("depth-3", joined)
            self.assertIn("D", joined)
        finally:
            db.close()


class PluginCanvasEntityTests(unittest.TestCase):
    def test_plugin_registered_entity_creates_resource(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        db, entity_service, _, _ = _stack(bus)
        try:
            created: list[dict] = []
            bus.subscribe(ENTITY_CREATED, lambda e: created.append(dict(e.payload)))
            bus.publish(
                PLUGIN_REGISTERED_ENTITY,
                {
                    "plugin_id": "notes",
                    "name": "Notes",
                    "description": "Vault notes",
                    "kind": "core",
                    "enabled": True,
                },
                source="tests",
            )
            self.assertEqual(1, len(created))
            self.assertEqual(ENTITY_TYPE_RESOURCE, created[0]["entity_type"])
            meta = created[0]["metadata"]
            self.assertEqual(RESOURCE_TYPE_PLUGIN, meta["resource_type"])
            self.assertEqual("notes", meta["plugin_id"])

            plugins = [
                e
                for e in store.snapshot.workspace_os.entities
                if dict(e.metadata).get("resource_type") == RESOURCE_TYPE_PLUGIN
            ]
            self.assertEqual(1, len(plugins))
            self.assertEqual("Notes", plugins[0].title)
        finally:
            db.close()

    def test_plugin_registered_entity_upserts_on_repeat(self) -> None:
        bus = EventBus()
        db, entity_service, _, _ = _stack(bus)
        try:
            bus.publish(
                PLUGIN_REGISTERED_ENTITY,
                {
                    "plugin_id": "shell",
                    "name": "Shell",
                    "description": "v1",
                    "kind": "extension",
                    "enabled": True,
                },
                source="tests",
            )
            updated: list[dict] = []
            bus.subscribe(ENTITY_UPDATED, lambda e: updated.append(dict(e.payload)))
            bus.publish(
                PLUGIN_REGISTERED_ENTITY,
                {
                    "plugin_id": "shell",
                    "name": "Shell Tools",
                    "description": "v2",
                    "kind": "extension",
                    "enabled": False,
                },
                source="tests",
            )
            resources = [
                e
                for e in entity_service.get_by_type(ENTITY_TYPE_RESOURCE)
                if dict(e.metadata).get("plugin_id") == "shell"
            ]
            self.assertEqual(1, len(resources))
            self.assertEqual("Shell Tools", resources[0].title)
            self.assertEqual("false", resources[0].metadata["enabled"])
            self.assertTrue(updated)
        finally:
            db.close()

    def test_plugin_registry_publishes_registered_entity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifests = Path(tmp)
            (manifests / "demo.yaml").write_text(
                "\n".join(
                    [
                        "id: demo",
                        "name: Demo Plugin",
                        "version: 0.1.0",
                        "description: Demo",
                        "kind: extension",
                        "enabled: true",
                        "bus_topics: []",
                    ]
                ),
                encoding="utf-8",
            )
            bus = EventBus()
            events: list[dict] = []
            bus.subscribe(
                PLUGIN_REGISTERED_ENTITY,
                lambda e: events.append(dict(e.payload)),
            )
            service = PluginRegistryService(bus, manifests_dir=manifests)
            service.start()
            try:
                self.assertTrue(any(e.get("plugin_id") == "demo" for e in events))
            finally:
                service.stop()


if __name__ == "__main__":
    unittest.main()
