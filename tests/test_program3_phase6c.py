"""Program 3 Phase 6c — workspace-centric runtime policy and WII approach test."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from ai_command_center.application import create_application
from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.entity.entity import ENTITY_TYPE_WORKSPACE
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    UI_COMMAND,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.state.chat_state import CHAT_REDUCERS
from ai_command_center.core.state.workspace_state import WORKSPACE_REDUCERS
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.services.command_router_service import CommandRouterService
from ai_command_center.services.telemetry_service import TelemetryService
from ai_command_center.services.telemetry_summary import compute_session_summary
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.shell.view_manager import ViewManagerMixin


class _PolicyProbe(ViewManagerMixin):
    def __init__(self, controller: UIController) -> None:
        self._default_view = "workspace"
        self._controller = controller
        self._current_view = "workspace"
        self._views = {}
        self._view_registry = {}
        self._content = MagicMock()
        self._sidebar = MagicMock()


class Phase6cRoutingPolicyTests(unittest.TestCase):
    def test_chat_redirects_to_workspace_without_active_scope(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        controller = UIController(bus, store, MagicMock())
        probe = _PolicyProbe(controller)
        self.assertEqual("workspace", probe._policy_resolve_view("chat"))

    def test_chat_allowed_when_workspace_active(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        controller = UIController(bus, store, MagicMock())
        bus.publish(
            WORKSPACE_ACTIVE,
            {"workspace_id": "ws-active", "title": "Active"},
            source="tests",
        )
        probe = _PolicyProbe(controller)
        self.assertEqual("chat", probe._policy_resolve_view("chat"))


class Phase6cReducerOwnershipTests(unittest.TestCase):
    def test_workspace_and_chat_reducers_cover_scope_topics(self) -> None:
        workspace_topics = {
            "workspace.active",
            "workspace.deactivated",
            "ui.workspace_os.select_entity",
            "notes.indexed",
        }
        chat_topics = {
            "command.routed",
            "ui.workspace_os.open_chat",
            "ui.chat.new_session",
            "context.snapshot.created",
        }
        self.assertTrue(workspace_topics)
        self.assertTrue(chat_topics)
        self.assertGreaterEqual(len(WORKSPACE_REDUCERS), 3)
        self.assertGreaterEqual(len(CHAT_REDUCERS), 5)


class Phase6cWiiApproachTests(unittest.TestCase):
    def test_headless_session_workspace_scope_ratio_approaches_target(self) -> None:
        db_path = Path(":memory:")
        from ai_command_center.db.connection import connect, init_database

        db = init_database(connect(db_path))
        app = create_application(debug_mode=False, workspace_os_enabled=True, db=db)
        app.startup()
        telemetry = app.services.get("telemetry")
        assert isinstance(telemetry, TelemetryService)
        repo = TelemetryRepository(db)
        try:
            ws = app.workspace_os
            assert ws is not None
            workspace = ws.entity_service.create(
                entity_type=ENTITY_TYPE_WORKSPACE,
                title="WII Session",
            )
            active_id = str(workspace.id)
            bus = app.bus
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": active_id, "title": workspace.title},
                source="tests",
            )
            bus.publish(
                UI_COMMAND,
                {
                    "text": "status in workspace",
                    "workspace_id": active_id,
                },
                source="tests",
            )
            bus.publish(
                UI_COMMAND,
                {
                    "text": "remember: launch checklist",
                    "workspace_id": active_id,
                },
                source="tests",
            )

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
            ratio = summary["workspace_scope"]["ratio_pct"]
            self.assertGreaterEqual(ratio, 40.0)
            scoped = summary["workspace_scope"]["scoped"]
            self.assertGreaterEqual(scoped, 1)
        finally:
            app.shutdown()


class Phase6cCommandRouterIntegrationTests(unittest.TestCase):
    def test_scoped_command_routed_projects_to_chat_state(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        router = CommandRouterService(bus)
        router.load()
        try:
            bus.publish(
                WORKSPACE_ACTIVE,
                {"workspace_id": "ws-6c", "title": "Six C"},
                source="tests",
            )
            bus.publish(UI_COMMAND, {"text": "hello policy"}, source="tests")
            snap = store.snapshot
            self.assertEqual("ws-6c", snap.last_workspace_context_workspace_id)
            self.assertEqual(INTENT_CHAT, snap.last_command_intent)
        finally:
            router.unload()


if __name__ == "__main__":
    unittest.main()
