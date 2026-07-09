"""Workflow graph AppState reducer tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_WORKFLOW_NODE_SELECT,
    WORKFLOW_COMPLETED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)
from ai_command_center.domain.workflow_graph import NodeState


def test_workflow_started_projects_graph() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            WORKFLOW_STARTED,
            {
                "run_id": "run-1",
                "workflow_id": "demo",
                "steps": [
                    {"id": "a", "name": "Plan"},
                    {"id": "b", "name": "Execute"},
                ],
            },
            source="test",
        )
        snap = store.snapshot
        assert snap.workflow_graph.workflow_id == "demo"
        assert snap.workflow_graph.run_id == "run-1"
        assert len(snap.workflow_graph.nodes) == 2
        assert snap.workflow_graph.running is True
    finally:
        store.close()


def test_workflow_step_events_update_node_overlay() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            WORKFLOW_STARTED,
            {
                "run_id": "run-2",
                "workflow_id": "demo",
                "steps": [{"id": "a", "name": "Plan"}, {"id": "b", "name": "Execute"}],
            },
            source="test",
        )
        bus.publish(
            WORKFLOW_STEP_STARTED,
            {"run_id": "run-2", "step_id": "a", "index": 0},
            source="test",
        )
        snap = store.snapshot
        assert snap.workflow_graph.nodes[0].state == NodeState.RUNNING.value

        bus.publish(
            WORKFLOW_STEP_COMPLETED,
            {"run_id": "run-2", "step_id": "a", "index": 0, "success": True},
            source="test",
        )
        snap = store.snapshot
        assert snap.workflow_graph.nodes[0].state == NodeState.COMPLETED.value
    finally:
        store.close()


def test_workflow_node_select_updates_selection() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            UI_WORKFLOW_NODE_SELECT,
            {"node_id": "node-1", "workflow_id": "demo", "label": "Plan"},
            source="ui",
        )
        snap = store.snapshot
        assert snap.workflow_graph.selected_node_id == "node-1"
    finally:
        store.close()


def test_workflow_completed_clears_running_flag() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            WORKFLOW_STARTED,
            {
                "run_id": "run-3",
                "workflow_id": "demo",
                "steps": [{"id": "a", "name": "Plan"}],
            },
            source="test",
        )
        bus.publish(WORKFLOW_COMPLETED, {"run_id": "run-3"}, source="test")
        assert store.snapshot.workflow_graph.running is False
    finally:
        store.close()
