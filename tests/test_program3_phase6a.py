"""Program 3 Phase 6a — workspace-required command spine (soft gate)."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.entity.entity import ENTITY_TYPE_WORKSPACE
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT, INTENT_NAVIGATE, INTENT_SHELL
from ai_command_center.core.events.topics import (
    COMMAND_DEFERRED,
    COMMAND_ROUTED,
    SERVICE_READY,
    TELEMETRY_EVENT,
    UI_COMMAND,
    UI_WORKSPACE_REQUIRED,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.workspace.workspace_service import WorkspaceService
from ai_command_center.db.connection import connect, init_database
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.services.telemetry_service import TelemetryService
from ai_command_center.services.telemetry_summary import compute_session_summary


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


class Phase6aSoftGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.router = CommandRouterService(self.bus)
        self.router.load()
        self.routed: list[dict] = []
        self.deferred: list[dict] = []
        self.workspace_required: list[dict] = []
        self.bus.subscribe(
            COMMAND_ROUTED,
            lambda e: self.routed.append(dict(e.payload))
            if e.source == "command_router"
            else None,
        )
        self.bus.subscribe(COMMAND_DEFERRED, lambda e: self.deferred.append(dict(e.payload)))
        self.bus.subscribe(
            UI_WORKSPACE_REQUIRED, lambda e: self.workspace_required.append(dict(e.payload))
        )

    def tearDown(self) -> None:
        self.router.unload()

    def test_chat_deferred_without_active_workspace(self) -> None:
        self.bus.publish(UI_COMMAND, {"text": "hello"}, source="tests")
        self.assertEqual([], self.routed)
        self.assertEqual(1, len(self.deferred))
        self.assertEqual(1, len(self.workspace_required))
        self.assertEqual(INTENT_CHAT, self.deferred[0].get("intent"))
        self.assertEqual("no_active_workspace", self.deferred[0].get("reason"))

    def test_shell_deferred_without_active_workspace(self) -> None:
        self.bus.publish(UI_COMMAND, {"text": "> echo hi"}, source="tests")
        self.assertEqual([], self.routed)
        self.assertEqual(INTENT_SHELL, self.deferred[0].get("intent"))

    def test_navigate_allowed_without_active_workspace(self) -> None:
        self.bus.publish(UI_COMMAND, {"text": "go settings"}, source="tests")
        self.assertEqual(1, len(self.routed))
        self.assertEqual([], self.deferred)
        self.assertEqual(INTENT_NAVIGATE, self.routed[0].get("intent"))

    def test_command_routed_includes_workspace_id_when_active(self) -> None:
        ws_id = uuid4().hex
        self.bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": ws_id, "title": "Scoped"},
            source="tests",
        )
        self.bus.publish(UI_COMMAND, {"text": "hello"}, source="tests")
        self.assertEqual(1, len(self.routed))
        payload = self.routed[0]
        self.assertEqual(INTENT_CHAT, payload.get("intent"))
        self.assertEqual(ws_id, payload.get("workspace_id"))
        args = payload.get("args") or {}
        self.assertEqual(ws_id, args.get("workspace_id"))


class Phase6aAutoActivateTests(unittest.TestCase):
    def test_auto_activate_first_workspace_on_workspace_os_ready(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        db, entity_service, workspace_service = _minimal_stack(bus)
        try:
            workspace = entity_service.create(
                entity_type=ENTITY_TYPE_WORKSPACE,
                title="Boot",
            )
            self.assertIsNone(workspace_service.get_active())
            bus.publish(SERVICE_READY, {"service": "workspace_os"}, source="workspace_os")
            self.assertEqual(str(workspace.id), store.snapshot.active_workspace_id)
            self.assertEqual("Boot", store.snapshot.active_workspace_title)
        finally:
            db.close()

    def test_auto_activate_skipped_when_workspace_already_active(self) -> None:
        bus = EventBus()
        db, entity_service, workspace_service = _minimal_stack(bus)
        try:
            first = entity_service.create(entity_type=ENTITY_TYPE_WORKSPACE, title="First")
            second = entity_service.create(entity_type=ENTITY_TYPE_WORKSPACE, title="Second")
            workspace_service.activate(second.id)
            bus.publish(SERVICE_READY, {"service": "workspace_os"}, source="workspace_os")
            active = workspace_service.get_active()
            self.assertIsNotNone(active)
            self.assertEqual(second.id, active.id)
            self.assertNotEqual(first.id, active.id)
        finally:
            db.close()


class Phase6aWiiMeasurementTests(unittest.TestCase):
    def test_session_summary_workspace_scope_after_scoped_command(self) -> None:
        bus = EventBus()
        router = CommandRouterService(bus)
        router.load()
        repo = TelemetryRepository(init_database(connect(Path(":memory:"))))
        telemetry = TelemetryService(bus, repo)
        telemetry.start()
        try:
            ws_id = uuid4().hex
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": ws_id, "title": "WII"},
                source="tests",
            )
            bus.publish(UI_COMMAND, {"text": "scoped prompt"}, source="tests")
            rows = repo.fetch_session(telemetry.session_id)
            summary = compute_session_summary(
                [
                    {
                        "event": row.event_type,
                        "timestamp": row.timestamp,
                        "payload": row.payload_dict(),
                    }
                    for row in rows
                ]
            )
            payloads = [row.payload_dict() for row in rows]
            routed_rows = [p for p in payloads if p.get("intent") == INTENT_CHAT]
            self.assertTrue(routed_rows)
            self.assertEqual(ws_id, routed_rows[0].get("workspace_id"))
            self.assertGreaterEqual(summary["workspace_scope"]["ratio_pct"], 50.0)
        finally:
            telemetry.stop()
            router.unload()


if __name__ == "__main__":
    unittest.main()
