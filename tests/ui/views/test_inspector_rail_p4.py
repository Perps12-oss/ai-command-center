"""R1 P4 — SelectionInspector composed onto InspectorDock as world_node."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
)
from ai_command_center.ui.views.world_model.selection_inspector_panel import (
    inspectable_ref_for_node,
    inspectable_ref_from_world_model,
)
from tests.ui.fake_ui import GraphWorkspaceView, WorldExplorerView


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


def test_inspectable_ref_from_world_model_includes_art12_fields() -> None:
    ref = inspectable_ref_from_world_model(_wm())
    assert ref is not None
    assert ref.kind == "world_node"
    assert ref.ref_id == "n1"
    payload = dict(ref.payload)
    assert payload["Entity ID"] == "n1"
    assert payload["Name"] == "Alpha"
    assert payload["Relationship Count"] == "1"
    assert "__section__:Attributes" in payload
    assert "__section__:Metadata" in payload


def test_selection_inspector_renders_thin_machine_payload() -> None:
    from ai_command_center.domain.inspectable import InspectableRef

    view = WorldExplorerView(None)
    panel = view._selection_inspector
    assert type(panel).__name__ == "SelectionInspectorPanel"
    panel.update(
        InspectableRef(
            kind="world_node",
            ref_id="n9",
            label="Thin",
            payload=(("node_id", "n9"), ("node_type", "note"), ("label", "Thin")),
        )
    )
    texts: list[str] = []
    for child in panel._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    joined = " ".join(texts)
    assert "n9" in joined
    assert "Thin" in joined
    assert "note" in joined


def test_inspectable_ref_for_node_ignores_selected_id() -> None:
    ref = inspectable_ref_for_node(_wm(), "n2")
    assert ref is not None
    assert ref.ref_id == "n2"
    assert dict(ref.payload)["Name"] == "Beta"


def test_world_explorer_hosts_inspector_dock() -> None:
    view = WorldExplorerView(None)
    assert type(view._inspector_dock).__name__ == "InspectorDock"
    assert view._inspector is view._selection_inspector
    assert hasattr(view, "show_inspector") and hasattr(view, "clear_inspector")
    view.apply_state(AppState(world_model=_wm()))
    assert view._inspector_dock.host._current_ref is not None
    assert view._inspector_dock.host._current_ref.ref_id == "n1"


def test_graph_workspace_hosts_inspector_dock() -> None:
    view = GraphWorkspaceView(None)
    assert type(view._inspector_dock).__name__ == "InspectorDock"
    assert view._inspector is view._selection_inspector
    view.apply_state(AppState(world_model=_wm()))
    assert view._inspector_dock.host._current_ref is not None
    assert view._inspector_dock.host._current_ref.kind == "world_node"
