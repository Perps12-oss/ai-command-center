"""UI tests for PR-UI-E12 Relationship Graph Workspace."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_GRAPH_FILTER,
    UI_GRAPH_NAVIGATE,
    UI_GRAPH_OPEN,
    UI_GRAPH_SELECT,
    WORLD_MODEL_NODE_SELECTED,
)
from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
)
from ai_command_center.ui.components.sidebar import NAV_GROUPS
from ai_command_center.ui.components.world_model.graph_renderer import (
    filtered_graph,
    graph_metrics,
)
from ai_command_center.ui.components.world_model.node_filters import NodeFilterState
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.shell.view_manager import VIEW_IDS
from tests.ui.fake_ui import GraphWorkspaceView


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
            NodeSnapshot(
                node_id="n3",
                node_type="note",
                label="Gamma",
                attributes=(("status", "active"),),
            ),
        ),
        edges=(
            EdgeSnapshot(
                edge_id="e1",
                from_node_id="n1",
                to_node_id="n2",
                edge_type="supports",
            ),
            EdgeSnapshot(
                edge_id="e2",
                from_node_id="n1",
                to_node_id="n3",
                edge_type="related",
            ),
        ),
        selected_node_id="n1",
        node_count=3,
    )


def test_graph_workspace_registered_in_nav_and_view_ids():
    assert "graph_workspace" in VIEW_IDS
    view_ids = [vid for _, items in NAV_GROUPS for vid, _ in items]
    assert "graph_workspace" in view_ids


def test_graph_workspace_filters_and_selection():
    inspected: list[object] = []
    filters: list[NodeFilterState] = []
    activated: list[str] = []
    navigated: list[str] = []
    view = GraphWorkspaceView(
        None,
        on_filter_change=filters.append,
        on_inspect_select=lambda ref: inspected.append(ref),
        on_activate=activated.append,
        on_navigate=navigated.append,
    )
    view.apply_state(AppState(world_model=_wm()))
    assert "3/3 nodes" in view._metrics.cget("text")
    assert view._graph is not None
    assert view._inspector is not None

    state = NodeFilterState(type_filter="note")
    view._on_filters(state)
    assert filters and filters[-1].type_filter == "note"
    assert "2/3 nodes" in view._metrics.cget("text")

    view._select("n1")
    assert inspected and getattr(inspected[-1], "kind") == "world_node"
    assert getattr(inspected[-1], "ref_id") == "n1"

    view._activate("n2")
    assert activated == ["n2"]
    assert inspected[-1].ref_id == "n2"


def test_filtered_graph_helper():
    wm = _wm()
    nodes, edges = filtered_graph(wm, NodeFilterState(type_filter="note"))
    assert {n.node_id for n in nodes} == {"n1", "n3"}
    assert {e.edge_id for e in edges} == {"e2"}
    assert "2/3 nodes · 1 edges" in graph_metrics(wm, nodes, edge_count=len(edges))


def test_controller_graph_intents():
    bus = EventBus()
    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[str] = []
    bus.subscribe(UI_GRAPH_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_GRAPH_FILTER, lambda e: seen.append(e.topic))
    bus.subscribe(UI_GRAPH_OPEN, lambda e: seen.append(e.topic))
    bus.subscribe(UI_GRAPH_NAVIGATE, lambda e: seen.append(e.topic))
    bus.subscribe(WORLD_MODEL_NODE_SELECTED, lambda e: seen.append(e.topic))
    controller.publish_graph_select("n1")
    controller.publish_world_model_node_selected("n1")
    controller.publish_graph_filter(type_filter="note")
    controller.publish_graph_open()
    controller.publish_graph_navigate("n1")
    assert seen == [
        UI_GRAPH_SELECT,
        WORLD_MODEL_NODE_SELECTED,
        UI_GRAPH_FILTER,
        UI_GRAPH_OPEN,
        UI_GRAPH_NAVIGATE,
    ]
