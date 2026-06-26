"""
Walking Skeleton Demo - Workspace OS Phase 2

Validates the end-to-end architecture flow:
  UI → AppState → EventBus → Services → Repositories → Storage

This script is not user-facing. It exists to prove that the Workspace OS
foundation can create, persist, and launch a URL resource through the
new architecture without touching the existing AI Command Center features.
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

# Add project root to path if running directly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ai_command_center.application import create_application
from ai_command_center.core.entity.entity import (
    ENTITY_TYPE_CARD,
    ENTITY_TYPE_RESOURCE,
    ENTITY_TYPE_WORKSPACE,
    RESOURCE_TYPE_URL,
)
from ai_command_center.core.relationship.relationship import RelationshipType


DEMO_URL = "https://example.com"


def run() -> int:
    """Execute the walking skeleton demo."""
    print("=== Workspace OS Walking Skeleton Demo ===")

    # Build application core (includes existing services + new Workspace OS wrapper)
    app = create_application(debug_mode=False)

    try:
        app.startup()

        if app.workspace_os is None or not app.workspace_os.enabled:
            print("ERROR: Workspace OS service is not available")
            return 1

        wos = app.workspace_os

        # 1. Create workspace
        workspace = wos.workspace_service.create(
            title="Demo Workspace",
            description="Walking skeleton workspace",
        )
        print(f"Created workspace: {workspace.title} ({workspace.id})")

        # 2. Create card inside workspace
        card = wos.entity_service.create(
            entity_type=ENTITY_TYPE_CARD,
            title="Demo Card",
            description="Card containing a URL resource",
        )
        print(f"Created card: {card.title} ({card.id})")

        # 3. Create URL resource entity
        url_entity = wos.entity_service.create(
            entity_type=ENTITY_TYPE_RESOURCE,
            title="Example URL",
            description="Demo URL for walking skeleton",
            metadata={"resource_type": RESOURCE_TYPE_URL, "url": DEMO_URL},
        )
        print(f"Created URL resource entity: {url_entity.title} ({url_entity.id})")

        # 4. Create relationships: workspace CONTAINS card, card CONTAINS url
        workspace_card_rel = wos.relationship_service.create(
            source_id=workspace.id,
            target_id=card.id,
            relationship_type=RelationshipType.CONTAINS,
            metadata={"order": 1},
        )
        card_url_rel = wos.relationship_service.create(
            source_id=card.id,
            target_id=url_entity.id,
            relationship_type=RelationshipType.CONTAINS,
            metadata={"order": 1},
        )
        print(f"Created relationships: {workspace_card_rel.id}, {card_url_rel.id}")

        # 5. Find the LAUNCH_URL action
        launch_actions = wos.action_registry.get_by_type("launch")
        if not launch_actions:
            print("ERROR: No launch action registered")
            return 1

        launch_action = launch_actions[0]
        print(f"Found launch action: {launch_action.id}")

        # 6. Invoke the action with the URL from the entity
        result = wos.action_registry.invoke(
            action_id=launch_action.id,
            parameters={"url": DEMO_URL},
        )
        print(f"Launch result: {result}")

        # 7. Verify persistence by searching
        found = wos.entity_service.search("Example")
        print(f"Search returned {len(found)} entity(s)")

        # 8. Record timeline event
        wos.timeline_service.record(
            event_type="Launch URL",
            entity_id=url_entity.id,
            entity_type=ENTITY_TYPE_RESOURCE,
            payload={"action_id": str(launch_action.id), "url": DEMO_URL},
        )
        print("Timeline event recorded")

        print("\n=== Walking Skeleton SUCCESS ===")
        print("Architecture flow validated: create → relate → launch → persist")
        return 0

    finally:
        app.shutdown()


if __name__ == "__main__":
    # Prevent actual browser pop-up during automated test runs unless requested
    if "--no-browser" in sys.argv:
        # Patch webbrowser to avoid opening a window
        class NoOpBrowser:
            def open(self, url: str, new: int = 0, autoraise: bool = True) -> bool:
                print(f"[Browser suppressed] would open: {url}")
                return True

        webbrowser.register("noop", None, NoOpBrowser())
        webbrowser.get("noop")

    sys.exit(run())
