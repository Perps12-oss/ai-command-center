"""UI tests for PR-UI-E08 World Model Explorer."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_WORLD_FILTER,
    UI_WORLD_OPEN,
    UI_WORLD_SELECT,
    WORLD_MODEL_NODE_SELECTED,
)
from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
)
from ai_command_center.ui.components.world_model.node_filters import (
    NodeFilterState,
    filter_nodes,
)
from ai_command_center.ui.controller import UIController
from tests.ui.fake_ui import WorldExplorerView


def _wm() -> WorldModelSnapshot:
    return WorldModelSnapshot(
        nodes=(
            NodeSnapshot(
                node_id="n1",
                node_type="note",
                label="Alpha",
                attributes=(("status", "active"),),
            ),
            NodeSnapshot(
                node_id="n2",
                node_type="goal",
                label="Beta",
                attributes=(("status", "paused"),),
            ),
        ),
        edges=(
            EdgeSnapshot(
                edge_id="e1",
                from_node_id="n1",
                to_node_id="n2",
                edge_type="supports",
            ),
        ),
        selected_node_id="n1",
        node_count=2,
    )


def test_world_explorer_filters_list_and_graph():
    inspected: list[object] = []
    filters: list[NodeFilterState] = []
    view = WorldExplorerView(
        None,
        on_filter_change=filters.append,
        on_inspect_select=lambda ref: inspected.append(ref),
    )
    view.apply_state(AppState(world_model=_wm()))
    assert "2 entities" in view._hero_state.cget("text")
    assert view._filters is not None
    assert view._graph is not None

    state = NodeFilterState(type_filter="note")
    view._on_filters(state)
    assert filters and filters[-1].type_filter == "note"
    assert "1 shown" in view._explorer._count.cget("text")

    view._select("n1")
    assert inspected and getattr(inspected[-1], "kind") == "world_node"


def test_filter_nodes_helper():
    nodes = _wm().nodes
    filtered = filter_nodes(nodes, NodeFilterState(type_filter="goal"))
    assert len(filtered) == 1 and filtered[0].node_id == "n2"
    filtered = filter_nodes(nodes, NodeFilterState(search="alp"))
    assert len(filtered) == 1 and filtered[0].node_id == "n1"


def test_controller_world_intents():
    bus = EventBus()
    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[str] = []
    bus.subscribe(UI_WORLD_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_WORLD_FILTER, lambda e: seen.append(e.topic))
    bus.subscribe(UI_WORLD_OPEN, lambda e: seen.append(e.topic))
    bus.subscribe(WORLD_MODEL_NODE_SELECTED, lambda e: seen.append(e.topic))
    controller.publish_world_select("n1")
    controller.publish_world_model_node_selected("n1")
    controller.publish_world_filter(type_filter="note")
    controller.publish_world_open()
    assert seen == [
        UI_WORLD_SELECT,
        WORLD_MODEL_NODE_SELECTED,
        UI_WORLD_FILTER,
        UI_WORLD_OPEN,
    ]
