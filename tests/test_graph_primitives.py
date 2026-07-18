"""Primitive reuse tests for shared graph canvas architecture."""

from __future__ import annotations

import ast
from pathlib import Path

from ai_command_center.ui.components.graph import (
    BaseGraphCanvas,
    GraphEdgeVisual,
    GraphNodeVisual,
    GraphSelection,
    circular_layout,
    radial_layout,
)
from ai_command_center.ui.components.graph_canvas import GraphCanvas


REPO = Path(__file__).resolve().parent.parent
UI = REPO / "ai_command_center" / "ui"


def test_shared_exports() -> None:
    assert BaseGraphCanvas is not None
    assert issubclass(GraphCanvas, BaseGraphCanvas)


def test_circular_layout_positions() -> None:
    positions = circular_layout(["a", "b", "c"], width=400, height=240, node_radius=22)
    assert set(positions) == {"a", "b", "c"}
    assert positions["a"][1] < positions["b"][1] or positions["a"][0] != positions["b"][0]


def test_radial_layout_center() -> None:
    positions = radial_layout("center", ["p1", "p2"], width=340, height=260)
    assert positions["center"] == (170.0, 130.0)
    assert "p1" in positions and "p2" in positions


def test_selection_toggle() -> None:
    sel = GraphSelection()
    sel.select_node("n1")
    assert sel.is_node_selected("n1")
    sel.select_node("n2", additive=True)
    assert sel.is_node_selected("n1") and sel.is_node_selected("n2")
    sel.select_edge("n1->n2")
    assert not sel.is_node_selected("n1")
    assert sel.is_edge_selected("n1->n2")


def test_node_bounds_oval_and_rect() -> None:
    rect = GraphNodeVisual(node_id="r", x=10, y=20, width=100, height=40, shape="rect")
    assert rect.bounds == (10, 20, 110, 60)
    assert rect.contains(50, 40)
    oval = GraphNodeVisual(node_id="o", x=50, y=50, width=40, height=40, shape="oval")
    assert oval.bounds == (30, 30, 70, 70)
    assert oval.contains(50, 50)


def test_edge_id_helper() -> None:
    assert GraphEdgeVisual.make_id("a", "b") == "a->b"


def _calls_canvas_primitives(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"create_oval", "create_line", "create_polygon"}:
                return True
    return False


def test_world_model_panel_has_no_local_canvas_engine() -> None:
    path = UI / "views" / "world_model" / "knowledge_graph_panel.py"
    source = path.read_text(encoding="utf-8")
    assert "BaseGraphCanvas" in source
    assert "circular_layout" in source
    assert not _calls_canvas_primitives(path)


def test_relationship_view_has_no_private_graph_canvas() -> None:
    path = UI / "views" / "relationship_view.py"
    source = path.read_text(encoding="utf-8")
    assert "BaseGraphCanvas" in source
    assert "class _GraphCanvas" not in source
    assert not _calls_canvas_primitives(path)


def test_workflow_adapter_reuses_base() -> None:
    path = UI / "components" / "graph_canvas.py"
    source = path.read_text(encoding="utf-8")
    assert "class GraphCanvas(BaseGraphCanvas)" in source
    assert "from ai_command_center.ui.components.graph import" in source


def test_shared_package_files_exist() -> None:
    root = UI / "components" / "graph"
    for name in (
        "base_graph_canvas.py",
        "graph_node.py",
        "graph_edge.py",
        "graph_selection.py",
        "graph_layout.py",
    ):
        assert (root / name).is_file(), name
