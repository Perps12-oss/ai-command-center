"""World-model graph projection helpers (PR-UI-E12) — no drawing engine."""

from __future__ import annotations

from collections.abc import Sequence

from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
)
from ai_command_center.ui.components.world_model.node_filters import (
    NodeFilterState,
    filter_nodes,
)


def filtered_graph(
    wm: WorldModelSnapshot,
    filter_state: NodeFilterState,
) -> tuple[list[NodeSnapshot], list[EdgeSnapshot]]:
    """Return filtered nodes and edges whose endpoints remain visible."""
    nodes = filter_nodes(wm.nodes, filter_state)
    visible = {n.node_id for n in nodes}
    edges = [
        e
        for e in wm.edges
        if e.from_node_id in visible and e.to_node_id in visible
    ]
    return nodes, edges


def graph_metrics(
    wm: WorldModelSnapshot,
    visible: Sequence[NodeSnapshot],
    *,
    edge_count: int | None = None,
) -> str:
    """Hero metric line for the graph workspace."""
    edges = len(wm.edges) if edge_count is None else int(edge_count)
    return f"{len(visible)}/{len(wm.nodes)} nodes · {edges} edges"


__all__ = ["filtered_graph", "graph_metrics"]
