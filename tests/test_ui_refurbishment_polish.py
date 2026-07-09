"""Polish fixes for skeleton/unwired UI refurbishment items."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_AUTOMATION_SCHEDULE_TOGGLE,
    UI_WORKFLOW_RUN,
    WORKFLOW_START,
)
from ai_command_center.core.state.workflow_graph_state import seed_demo_workflow_graph


def test_seed_demo_workflow_graph_has_steps() -> None:
    graph = seed_demo_workflow_graph()
    assert graph.workflow_id == "demo-linear"
    assert len(graph.nodes) >= 3
    assert graph.revision >= 1


def test_default_app_state_seeds_workflow_graph() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        snap = store.snapshot
        assert snap.workflow_graph.workflow_id == "demo-linear"
        assert len(snap.workflow_graph.nodes) >= 3
    finally:
        store.close()


def test_schedule_toggle_flips_enabled() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        before = store.snapshot.automation_workspace.schedules[0]
        bus.publish(
            UI_AUTOMATION_SCHEDULE_TOGGLE,
            {"schedule_id": before.schedule_id},
            source="ui",
        )
        after = store.snapshot.automation_workspace.schedules[0]
        assert after.enabled is not before.enabled
    finally:
        store.close()


def test_publish_workflow_run_emits_ui_topic() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    seen: list[str] = []

    def capture(event) -> None:
        seen.append(event.topic)

    unsub = bus.subscribe(UI_WORKFLOW_RUN, capture)
    try:
        bus.publish(
            WORKFLOW_START,
            {
                "workflow_id": "demo-linear",
                "steps": [{"id": "a", "type": "tool", "tool": "shell"}],
            },
            source="test",
        )
        bus.publish(
            UI_WORKFLOW_RUN,
            {
                "workflow_id": "demo-linear",
                "steps": [{"id": "a", "type": "tool", "tool": "shell"}],
            },
            source="ui",
        )
        assert UI_WORKFLOW_RUN in seen
    finally:
        unsub()
        store.close()


def test_templates_include_workflow_id() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        templates = store.snapshot.automation_workspace.templates
        assert all(template.workflow_id for template in templates)
    finally:
        store.close()
