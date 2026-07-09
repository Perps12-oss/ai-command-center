"""Unit tests for Workspace OS Phase 2 walking skeleton integration."""

from __future__ import annotations

import unittest
import webbrowser
from pathlib import Path
from uuid import UUID

from ai_command_center.application import create_application
from ai_command_center.core.entity.entity import (
    ENTITY_TYPE_CARD,
    ENTITY_TYPE_RESOURCE,
    ENTITY_TYPE_WORKSPACE,
    RESOURCE_TYPE_URL,
)
from ai_command_center.core.events.topics import (
    UI_CREATE_CARD,
    UI_CREATE_RESOURCE,
    UI_CREATE_WORKSPACE,
    UI_LAUNCH_RESOURCE,
)
from ai_command_center.core.relationship.relationship import RelationshipType
from ai_command_center.db.connection import connect, init_database
from ai_command_center.ui.workspace_os_controller import WorkspaceOsUIController


class NoOpBrowser:
    """Browser controller that suppresses actual browser launches during tests."""

    def __init__(self, controller: object) -> None:
        self._controller = controller
        self.last_url: str | None = None

    def open(
        self, url: str, new: int = 0, autoraise: bool = True
    ) -> bool:  # noqa: ARG002
        self.last_url = url
        return True


def _suppress_webbrowser() -> None:
    """Register a no-op browser controller for the test process."""
    noop = NoOpBrowser(object())
    webbrowser.register("noop", None, noop)
    webbrowser.get("noop")


class WorkspaceOsWalkingSkeletonTests(unittest.TestCase):
    """Validate the backend walking skeleton end-to-end."""

    @classmethod
    def setUpClass(cls) -> None:
        _suppress_webbrowser()

    def _create_app(self, workspace_os_enabled: bool = True):
        """Create a fresh in-memory application core for isolated tests."""
        db = init_database(connect(Path(":memory:")))
        return create_application(
            debug_mode=False,
            workspace_os_enabled=workspace_os_enabled,
            db=db,
        )

    def test_application_core_exposes_workspace_os(self) -> None:
        app = self._create_app()
        try:
            app.startup()
            self.assertIsNotNone(app.workspace_os)
            self.assertTrue(app.workspace_os.enabled)
        finally:
            app.shutdown()

    def test_workspace_os_can_be_disabled(self) -> None:
        app = self._create_app(workspace_os_enabled=False)
        try:
            app.startup()
            self.assertIsNone(app.workspace_os)
            # Existing services still load correctly
            self.assertIn("ollama", app.services.names())
        finally:
            app.shutdown()

    def test_create_workspace_card_url_flow(self) -> None:
        app = self._create_app()
        try:
            app.startup()
            wos = app.workspace_os
            assert wos is not None

            workspace = wos.workspace_service.create(
                title="Test Workspace",
                description="Unit test workspace",
            )
            self.assertEqual(ENTITY_TYPE_WORKSPACE, workspace.entity_type)

            card = wos.entity_service.create(
                entity_type=ENTITY_TYPE_CARD,
                title="Test Card",
                description="Unit test card",
            )
            self.assertEqual(ENTITY_TYPE_CARD, card.entity_type)

            url_entity = wos.entity_service.create(
                entity_type=ENTITY_TYPE_RESOURCE,
                title="Test URL",
                description="Unit test URL",
                metadata={
                    "resource_type": RESOURCE_TYPE_URL,
                    "url": "https://example.com/test",
                },
            )
            self.assertEqual(ENTITY_TYPE_RESOURCE, url_entity.entity_type)
            self.assertEqual(RESOURCE_TYPE_URL, url_entity.metadata["resource_type"])

            # Relate workspace -> card -> url
            rel1 = wos.relationship_service.create(
                source_id=workspace.id,
                target_id=card.id,
                relationship_type=RelationshipType.CONTAINS,
            )
            rel2 = wos.relationship_service.create(
                source_id=card.id,
                target_id=url_entity.id,
                relationship_type=RelationshipType.CONTAINS,
            )
            self.assertEqual(RelationshipType.CONTAINS, rel1.relationship_type)
            self.assertEqual(RelationshipType.CONTAINS, rel2.relationship_type)

            # Search should find the URL by title
            results = wos.entity_service.search("Test URL")
            found_ids = {r.id for r in results}
            self.assertIn(url_entity.id, found_ids)
        finally:
            app.shutdown()

    def test_launch_url_action_exists_and_runs(self) -> None:
        app = self._create_app()
        try:
            app.startup()
            wos = app.workspace_os
            assert wos is not None

            actions = wos.action_registry.get_by_type("launch")
            url_actions = [a for a in actions if a.name == "Launch URL"]
            self.assertEqual(1, len(url_actions))

            action = url_actions[0]
            result = wos.action_registry.invoke(
                action_id=action.id,
                parameters={"url": "https://example.com/test-launch"},
            )
            self.assertTrue(result["success"])
            self.assertEqual("https://example.com/test-launch", result["url"])
        finally:
            app.shutdown()

    def test_timeline_records_walking_skeleton_events(self) -> None:
        app = self._create_app()
        try:
            app.startup()
            wos = app.workspace_os
            assert wos is not None

            url_entity = wos.entity_service.create(
                entity_type=ENTITY_TYPE_RESOURCE,
                title="Timeline URL",
                description="For timeline test",
                metadata={
                    "resource_type": RESOURCE_TYPE_URL,
                    "url": "https://example.com/timeline",
                },
            )

            wos.timeline_service.record(
                event_type="Launch URL",
                entity_id=url_entity.id,
                entity_type=ENTITY_TYPE_RESOURCE,
                payload={"url": "https://example.com/timeline"},
            )

            events = wos.timeline_service.get_by_entity(url_entity.id)
            self.assertEqual(1, len(events))
            self.assertEqual("Launch URL", events[0].event_type)
        finally:
            app.shutdown()

    def test_ui_controller_creates_workspace(self) -> None:
        app = self._create_app()
        try:
            app.startup()
            controller = WorkspaceOsUIController(app.bus)
            controller.create_workspace("UI Workspace", "Created by UI controller")

            wos = app.workspace_os
            assert wos is not None
            workspaces = wos.workspace_service.get_all()
            self.assertEqual(1, len(workspaces))
            self.assertEqual("UI Workspace", workspaces[0].title)
        finally:
            app.shutdown()

    def test_ui_controller_creates_and_launches_resource(self) -> None:
        app = self._create_app()
        try:
            app.startup()
            wos = app.workspace_os
            assert wos is not None

            # Seed a workspace and card
            workspace = wos.workspace_service.create("Test Workspace")
            card = wos.entity_service.create(
                entity_type=ENTITY_TYPE_CARD,
                title="Test Card",
            )
            wos.workspace_service.add_entity(workspace.id, card.id)

            controller = WorkspaceOsUIController(app.bus)
            controller.create_resource(
                card_id=str(card.id),
                title="UI URL",
                resource_type=RESOURCE_TYPE_URL,
                value="https://example.com/ui",
            )

            resources = wos.entity_service.get_by_type(ENTITY_TYPE_RESOURCE)
            self.assertEqual(1, len(resources))
            self.assertEqual(RESOURCE_TYPE_URL, resources[0].metadata["resource_type"])

            controller.launch_resource(
                resource_id=str(resources[0].id),
                resource_type=RESOURCE_TYPE_URL,
                value="https://example.com/ui",
            )

            events = wos.timeline_service.get_by_entity(resources[0].id)
            launch_events = [event for event in events if event.event_type == "Launch URL"]
            self.assertEqual(1, len(launch_events))
            self.assertEqual("Launch URL", launch_events[0].event_type)
        finally:
            app.shutdown()

    def test_app_state_tracks_workspace_os_counters(self) -> None:
        app = self._create_app()
        try:
            app.startup()
            wos = app.workspace_os
            assert wos is not None

            wos.workspace_service.create("State Workspace")
            wos.timeline_service.record(event_type="Launch URL")

            snapshot = app.state_store.snapshot.workspace_os
            self.assertGreaterEqual(snapshot.entity_count, 1)
            self.assertGreaterEqual(snapshot.event_count, 1)
            self.assertIn("Launch URL", snapshot.recent_events)
        finally:
            app.shutdown()


if __name__ == "__main__":
    unittest.main()
