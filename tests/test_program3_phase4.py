"""Program 3 Phase 4 — workspace-scoped memory defaults and entity keys."""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MEMORY_REMEMBER,
    MEMORY_STORED,
    WORKSPACE_ACTIVE,
)
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
)
from ai_command_center.repositories.memory_repository import MemoryRepository
from ai_command_center.services.memory_graph_service import MemoryGraphService


class Phase4MemoryScopeTests(unittest.TestCase):
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

    def test_search_defaults_to_active_workspace_without_global_opt_in(self) -> None:
        self.repo.remember(label="a", content="alpha", workspace_id="ws-a")
        self.repo.remember(label="b", content="alpha", workspace_id="ws-b")

        self.bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-a", "title": "A"},
            source="tests",
        )

        scoped = self.repo.search("alpha", workspace_id="ws-a")
        implicit = self.repo.search("alpha")
        global_hits = self.repo.search("alpha", global_search=True)

        self.assertEqual(1, len(scoped))
        self.assertEqual("a", scoped[0].label)
        self.assertEqual(0, len(implicit))
        self.assertEqual(2, len(global_hits))

    def test_remember_defaults_workspace_from_active_scope(self) -> None:
        self.bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-active", "title": "Active"},
            source="tests",
        )
        stored: list[dict] = []
        self.bus.subscribe(MEMORY_STORED, lambda e: stored.append(dict(e.payload)))

        self.bus.publish(
            MEMORY_REMEMBER,
            {"label": "decision", "content": "scope me"},
            source="tests",
        )

        self.assertEqual(1, len(stored))
        self.assertEqual("ws-active", stored[0].get("workspace_id"))
        rows = self.repo.search("scope", workspace_id="ws-active")
        self.assertEqual(1, len(rows))
        self.assertEqual(0, len(self.repo.search("scope", workspace_id="ws-other")))

    def test_entity_scoped_search_within_workspace(self) -> None:
        self.repo.remember(
            label="card-note",
            content="entity scoped",
            workspace_id="ws-1",
            entity_id="card-1",
        )
        self.repo.remember(
            label="ws-note",
            content="entity scoped",
            workspace_id="ws-1",
            entity_id="",
        )

        card_hits = self.repo.search(
            "scoped",
            workspace_id="ws-1",
            entity_id="card-1",
        )
        ws_hits = self.repo.search("scoped", workspace_id="ws-1")

        self.assertEqual(1, len(card_hits))
        self.assertEqual("card-note", card_hits[0].label)
        self.assertEqual(2, len(ws_hits))

    def test_lookup_request_inherits_active_workspace(self) -> None:
        self.repo.remember(label="k1", content="lookup-me", workspace_id="ws-1")
        self.repo.remember(label="k2", content="lookup-me", workspace_id="ws-2")
        self.bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-1", "title": "One"},
            source="tests",
        )
        results: list[dict] = []
        self.bus.subscribe(MEMORY_LOOKUP_RESULT, lambda e: results.append(dict(e.payload)))

        self.bus.publish(
            MEMORY_LOOKUP_REQUEST,
            {"request_id": "r1", "query": "lookup"},
            source="tests",
        )

        self.assertEqual(1, len(results))
        self.assertIn("k1", results[0]["snippets"][0])
        self.assertNotIn("k2", results[0]["snippets"][0])

    def test_memory_catalog_filtered_by_active_workspace(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        bus.publish(
            MEMORY_STORED,
            {"id": "m1", "label": "ws-a", "workspace_id": "ws-a"},
            source="tests",
        )
        bus.publish(
            MEMORY_STORED,
            {"id": "m2", "label": "ws-b", "workspace_id": "ws-b"},
            source="tests",
        )
        self.assertEqual(2, len(store.snapshot.memory_catalog))

        bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-a", "title": "A"},
            source="tests",
        )
        catalog = store.snapshot.memory_catalog
        self.assertEqual(1, len(catalog))
        self.assertEqual("ws-a", catalog[0].label)
        self.assertEqual("ws-a", catalog[0].workspace_id)


class Phase4HeadlessIntegrationTests(unittest.TestCase):
    def test_memory_remember_with_entity_scope_via_service(self) -> None:
        bus = EventBus()
        db = init_database(connect(Path(":memory:")))
        try:
            repo = MemoryRepository(db)
            service = MemoryGraphService(bus, repo)
            service.load()
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": "ws-9", "title": "Nine"},
                source="tests",
            )
            bus.publish(
                MEMORY_REMEMBER,
                {
                    "label": "entity-fact",
                    "content": "pinned to card",
                    "workspace_entity_id": "card-9",
                },
                source="tests",
            )
            service.unload()
            rows = repo.search(
                "pinned",
                workspace_id="ws-9",
                entity_id="card-9",
            )
            self.assertEqual(1, len(rows))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
