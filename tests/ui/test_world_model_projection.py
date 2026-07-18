"""Projection tests for Phase 11B World Model workspace."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    GoalSnapshot,
    MutationSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
)
from ai_command_center.ui.design_system import theme_v2 as T
from tests.ui.fake_ui import WorldExplorerView


def _sample_wm(*, selected: str = "n1", mutations: int = 3) -> WorldModelSnapshot:
    nodes = (
        NodeSnapshot(
            node_id="n1",
            node_type="note",
            label="Alpha",
            attributes=(("status", "active"), ("workspace_id", "ws1")),
        ),
        NodeSnapshot(
            node_id="n2",
            node_type="goal",
            label="Beta",
            attributes=(("status", "active"),),
        ),
    )
    edges = (
        EdgeSnapshot(
            edge_id="e1",
            from_node_id="n1",
            to_node_id="n2",
            edge_type="supports",
            from_label="Alpha",
            to_label="Beta",
        ),
    )
    log = tuple(
        MutationSnapshot(
            mutation_id=f"m{i}",
            mutation_type="upsert",
            correlation_id=f"c{i}",
            goal_id="g1",
            timestamp=f"2024-01-01T00:00:{i:02d}",
            summary=f"mutation {i}",
        )
        for i in range(mutations)
    )
    return WorldModelSnapshot(
        nodes=nodes,
        edges=edges,
        mutation_log=log,
        goals=(GoalSnapshot(goal_id="g1", title="Ship", status="active"),),
        selected_node_id=selected,
        node_count=2,
        mutation_count=len(log),
    )


def test_hero_projection_counts() -> None:
    selected: list[str] = []
    created: list[bool] = []
    view = WorldExplorerView(
        None,
        on_select=selected.append,
        on_create_entity=lambda: created.append(True),
    )
    view.apply_state(AppState(world_model=_sample_wm()))

    assert "2 entities" in view._hero_state.cget("text")
    assert "1 relationships" in view._hero_state.cget("text")
    assert "1 active goals" in view._hero_goals.cget("text")


def test_selection_updates_inspector_and_relationships() -> None:
    view = WorldExplorerView(None, on_select=lambda _i: None)
    view.apply_state(_sample_wm(selected="n1"))

    # Inspector should show selected entity id
    body_texts = [
        child.cget("text")
        for child in view._inspector._body.winfo_children()
        for grandchild in getattr(child, "winfo_children", lambda: [])()
        for child in (grandchild,)
        if hasattr(child, "cget")
    ]
    # Flatten row labels/values from inspector body
    texts: list[str] = []
    for child in view._inspector._body.winfo_children():
        if hasattr(child, "cget"):
            try:
                texts.append(str(child.cget("text")))
            except Exception:
                pass
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    joined = " ".join(texts)
    assert "n1" in joined
    assert "Alpha" in joined

    rel_texts: list[str] = []
    for child in view._relationships._body.winfo_children():
        if hasattr(child, "cget"):
            try:
                rel_texts.append(str(child.cget("text")))
            except Exception:
                pass
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    rel_texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    assert any("Outgoing" in t or "Beta" in t or "supports" in t for t in rel_texts)


def test_mutation_journal_cap_200() -> None:
    view = WorldExplorerView(None)
    wm = _sample_wm(mutations=250)
    # Snapshot domain already caps at 200 in reducer; enforce panel uses last 200
    capped = WorldModelSnapshot(
        nodes=wm.nodes,
        edges=wm.edges,
        mutation_log=wm.mutation_log[-200:] if len(wm.mutation_log) > 200 else wm.mutation_log,
        goals=wm.goals,
        selected_node_id=wm.selected_node_id,
        node_count=wm.node_count,
        mutation_count=min(250, 200),
    )
    # Build an oversized log to prove panel caps
    oversized = tuple(
        MutationSnapshot(mutation_id=f"m{i}", mutation_type="upsert", summary=f"s{i}")
        for i in range(250)
    )
    view.apply_state(
        WorldModelSnapshot(
            nodes=wm.nodes,
            edges=wm.edges,
            mutation_log=oversized,
            goals=wm.goals,
            selected_node_id="",
            node_count=2,
            mutation_count=250,
        )
    )
    assert view._journal._count_label.cget("text") == "200"
    assert len(view._journal._entries) == 200
    _ = capped  # silence lint if unused in some runners


def test_world_teal_token_used() -> None:
    import ai_command_center.ui.views.world_explorer_view as shell
    import ai_command_center.ui.views.world_model.knowledge_graph_panel as graph

    # Modules may be unbound from sys.modules after fake_ui restore; inspect source files
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    files = [
        root / "ai_command_center/ui/views/world_explorer_view.py",
        root / "ai_command_center/ui/views/world_model/knowledge_graph_panel.py",
        root / "ai_command_center/ui/views/world_model/entity_explorer_panel.py",
        root / "ai_command_center/ui/views/world_model/selection_inspector_panel.py",
        root / "ai_command_center/ui/views/world_model/relationship_explorer_panel.py",
        root / "ai_command_center/ui/views/world_model/mutation_journal_panel.py",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "WORLD_TEAL" in text, f"{path.name} missing WORLD_TEAL"
        # No ad-hoc hex outside theme usage in panel constructors (token-only accent)
        assert "#009688" not in text, f"{path.name} hardcodes teal hex"

    assert T.WORLD_TEAL == "#009688"
    _ = shell, graph


def test_node_click_publishes_selection() -> None:
    selected: list[str] = []
    view = WorldExplorerView(None, on_select=selected.append)
    view.apply_state(_sample_wm())
    view._select("n2")
    assert selected == ["n2"]


def test_hero_new_entity_publishes_create() -> None:
    created: list[bool] = []
    view = WorldExplorerView(
        None,
        on_create_entity=lambda: created.append(True),
    )
    view._new_entity_btn.invoke()
    assert created == [True]


def test_no_world_model_state_listener_in_view() -> None:
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2]
        / "ai_command_center/ui/views/world_explorer_view.py"
    ).read_text(encoding="utf-8")
    assert "from ai_command_center.core.state.world_model_state" not in text
    assert "add_listener" not in text
    assert "WORLD_MODEL_MUTATION_APPLIED" not in text
    assert "EventBus" not in text
