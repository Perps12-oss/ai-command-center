"""Tests for the World Model UI state layer (P3).

Verifies WorldModelState projection logic. No Tkinter required.
"""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ENTITY_CREATED,
    ENTITY_DELETED,
    ENTITY_UPDATED,
    GOAL_ACTIVATED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    GOAL_SUBMITTED,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
    WORLD_MODEL_GRAPH_REFRESHED,
    WORLD_MODEL_NODE_DESELECTED,
    WORLD_MODEL_NODE_SELECTED,
)
from ai_command_center.core.state.world_model_state import WorldModelState


def _bus_and_state() -> tuple[EventBus, WorldModelState]:
    bus = EventBus()
    state = WorldModelState(bus)
    return bus, state


# ── node projection ────────────────────────────────────────────────────────


def test_entity_created_adds_node() -> None:
    bus, state = _bus_and_state()
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "My Resource"}, source="test")
    assert len(state.nodes) == 1
    assert state.nodes[0].node_id == "n-1"
    assert state.nodes[0].label == "My Resource"
    assert state.nodes[0].node_type == "resource"


def test_entity_updated_updates_node() -> None:
    bus, state = _bus_and_state()
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "Old Name"}, source="test")
    bus.publish(ENTITY_UPDATED, {"id": "n-1", "entity_type": "resource", "name": "New Name"}, source="test")
    assert len(state.nodes) == 1
    assert state.nodes[0].label == "New Name"


def test_entity_deleted_removes_node() -> None:
    bus, state = _bus_and_state()
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "X"}, source="test")
    bus.publish(ENTITY_DELETED, {"id": "n-1"}, source="test")
    assert state.nodes == []


def test_entity_deleted_clears_selection() -> None:
    bus, state = _bus_and_state()
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "X"}, source="test")
    bus.publish(WORLD_MODEL_NODE_SELECTED, {"node_id": "n-1"}, source="test")
    assert state.selected_node_id == "n-1"
    bus.publish(ENTITY_DELETED, {"id": "n-1"}, source="test")
    assert state.selected_node_id is None


def test_multiple_entities_independent() -> None:
    bus, state = _bus_and_state()
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "workspace", "name": "WS1"}, source="test")
    bus.publish(ENTITY_CREATED, {"id": "n-2", "entity_type": "goal", "name": "Goal A"}, source="test")
    bus.publish(ENTITY_CREATED, {"id": "n-3", "entity_type": "resource", "name": "Res B"}, source="test")
    assert len(state.nodes) == 3
    ids = {n.node_id for n in state.nodes}
    assert ids == {"n-1", "n-2", "n-3"}


# ── selection ──────────────────────────────────────────────────────────────


def test_node_selected_sets_selected_id() -> None:
    bus, state = _bus_and_state()
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "X"}, source="test")
    bus.publish(WORLD_MODEL_NODE_SELECTED, {"node_id": "n-1"}, source="test")
    assert state.selected_node_id == "n-1"
    assert state.selected_node is not None
    assert state.selected_node.node_id == "n-1"


def test_node_deselected_clears_selection() -> None:
    bus, state = _bus_and_state()
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "X"}, source="test")
    bus.publish(WORLD_MODEL_NODE_SELECTED, {"node_id": "n-1"}, source="test")
    bus.publish(WORLD_MODEL_NODE_DESELECTED, {}, source="test")
    assert state.selected_node_id is None
    assert state.selected_node is None


def test_selected_node_nonexistent_returns_none() -> None:
    bus, state = _bus_and_state()
    bus.publish(WORLD_MODEL_NODE_SELECTED, {"node_id": "ghost"}, source="test")
    assert state.selected_node is None


# ── graph refresh ──────────────────────────────────────────────────────────


def test_graph_refreshed_replaces_all_nodes() -> None:
    bus, state = _bus_and_state()
    bus.publish(ENTITY_CREATED, {"id": "old-1", "entity_type": "resource", "name": "Old"}, source="test")
    bus.publish(WORLD_MODEL_GRAPH_REFRESHED, {
        "nodes": [
            {"id": "n-1", "type": "workspace", "label": "WS"},
            {"id": "n-2", "type": "goal", "label": "Goal"},
        ],
        "edges": [
            {"id": "e-1", "from_node_id": "n-1", "to_node_id": "n-2", "type": "contains"},
        ],
    }, source="test")
    assert len(state.nodes) == 2
    ids = {n.node_id for n in state.nodes}
    assert ids == {"n-1", "n-2"}
    assert "old-1" not in ids


def test_graph_refreshed_populates_edges_for_selected() -> None:
    bus, state = _bus_and_state()
    bus.publish(WORLD_MODEL_GRAPH_REFRESHED, {
        "nodes": [
            {"id": "n-1", "type": "workspace", "label": "WS"},
            {"id": "n-2", "type": "goal", "label": "Goal"},
        ],
        "edges": [
            {"id": "e-1", "from_node_id": "n-1", "to_node_id": "n-2", "type": "contains"},
        ],
    }, source="test")
    bus.publish(WORLD_MODEL_NODE_SELECTED, {"node_id": "n-1"}, source="test")
    edges = state.edges_for_selected
    assert len(edges) == 1
    assert edges[0].edge_id == "e-1"
    assert edges[0].edge_type == "contains"


# ── mutation log ───────────────────────────────────────────────────────────


def test_mutation_applied_appended_to_log() -> None:
    bus, state = _bus_and_state()
    bus.publish(RUNTIME_WORLD_MODEL_APPLY_COMPLETED, {
        "mutation": {
            "id": "m-1",
            "type": "create_node",
            "correlation_id": "c-1",
            "goal_id": "g-1",
            "created_at": "2026-07-13T10:00:00+00:00",
            "payload": {"node": {"id": "n-1"}},
        }
    }, source="test")
    log = state.mutation_log
    assert len(log) == 1
    assert log[0].mutation_id == "m-1"
    assert log[0].mutation_type == "create_node"
    assert log[0].goal_id == "g-1"


def test_mutation_log_newest_first() -> None:
    bus, state = _bus_and_state()
    for i in range(3):
        bus.publish(RUNTIME_WORLD_MODEL_APPLY_COMPLETED, {
            "mutation": {"id": f"m-{i}", "type": "create_node", "payload": {}}
        }, source="test")
    log = state.mutation_log
    assert log[0].mutation_id == "m-2"
    assert log[-1].mutation_id == "m-0"


# ── goal projection ────────────────────────────────────────────────────────


def test_goal_submitted_appears_in_active_goals() -> None:
    bus, state = _bus_and_state()
    bus.publish(GOAL_SUBMITTED, {
        "goal": {"id": "g-1", "title": "Do something", "status": "queued"}
    }, source="test")
    goals = state.active_goals
    assert len(goals) == 1
    assert goals[0].goal_id == "g-1"
    assert goals[0].title == "Do something"


def test_completed_goal_not_in_active_goals() -> None:
    bus, state = _bus_and_state()
    bus.publish(GOAL_SUBMITTED, {"goal": {"id": "g-1", "title": "Done goal", "status": "queued"}}, source="test")
    bus.publish(GOAL_COMPLETED, {"goal_id": "g-1", "goal": {"id": "g-1", "title": "Done goal", "status": "complete"}}, source="test")
    assert state.active_goals == []


def test_failed_goal_not_in_active_goals() -> None:
    bus, state = _bus_and_state()
    bus.publish(GOAL_ACTIVATED, {"goal": {"id": "g-2", "title": "Fail goal", "status": "active"}}, source="test")
    bus.publish(GOAL_FAILED, {"goal_id": "g-2", "goal": {"id": "g-2", "title": "Fail goal", "status": "failed"}}, source="test")
    assert state.active_goals == []


# ── listener notifications ─────────────────────────────────────────────────


def test_listener_notified_on_entity_created() -> None:
    bus, state = _bus_and_state()
    calls: list[int] = []
    state.add_listener(lambda: calls.append(1))
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "X"}, source="test")
    assert len(calls) == 1


def test_listener_unsubscribe_stops_notifications() -> None:
    bus, state = _bus_and_state()
    calls: list[int] = []
    remove = state.add_listener(lambda: calls.append(1))
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "X"}, source="test")
    assert len(calls) == 1
    remove()
    bus.publish(ENTITY_CREATED, {"id": "n-2", "entity_type": "resource", "name": "Y"}, source="test")
    assert len(calls) == 1


def test_dispose_removes_all_bus_subscriptions() -> None:
    bus, state = _bus_and_state()
    state.dispose()
    bus.publish(ENTITY_CREATED, {"id": "n-1", "entity_type": "resource", "name": "X"}, source="test")
    assert state.nodes == []
