"""Layered layout for workflow DAG graphs."""

from __future__ import annotations

from collections import deque

from ai_command_center.domain.workflow_graph import GraphNode, WorkflowGraph

_LAYER_X = 180.0
_LAYER_Y = 72.0
_ORIGIN_X = 40.0
_ORIGIN_Y = 48.0


def layout_workflow_graph(graph: WorkflowGraph) -> WorkflowGraph:
    """Assign x/y positions using a simple layered DAG layout."""
    if not graph.nodes:
        return graph

    node_ids = {node.node_id for node in graph.nodes}
    in_degree: dict[str, int] = {node_id: 0 for node_id in node_ids}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}

    for edge in graph.edges:
        if edge.source_id in node_ids and edge.target_id in node_ids:
            adjacency[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

    roots = [node_id for node_id, degree in in_degree.items() if degree == 0]
    if not roots:
        roots = [graph.nodes[0].node_id]

    depth: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque((root, 0) for root in roots)
    while queue:
        node_id, level = queue.popleft()
        if node_id in depth and depth[node_id] >= level:
            continue
        depth[node_id] = level
        for target in adjacency.get(node_id, []):
            queue.append((target, level + 1))

    max_depth = max(depth.values()) if depth else 0
    for node in graph.nodes:
        if node.node_id not in depth:
            max_depth += 1
            depth[node.node_id] = max_depth

    layers: dict[int, list[str]] = {}
    for node_id, level in depth.items():
        layers.setdefault(level, []).append(node_id)

    positioned: list[GraphNode] = []
    for level in sorted(layers):
        ids = layers[level]
        for index, node_id in enumerate(ids):
            node = graph.node_by_id(node_id)
            if node is None:
                continue
            positioned.append(
                GraphNode(
                    node_id=node.node_id,
                    label=node.label,
                    kind=node.kind,
                    state=node.state,
                    description=node.description,
                    metadata=dict(node.metadata),
                    x=_ORIGIN_X + level * _LAYER_X,
                    y=_ORIGIN_Y + index * _LAYER_Y,
                )
            )

    orphan_ids = node_ids - {node.node_id for node in positioned}
    for index, node_id in enumerate(sorted(orphan_ids)):
        node = graph.node_by_id(node_id)
        if node is None:
            continue
        positioned.append(
            GraphNode(
                node_id=node.node_id,
                label=node.label,
                kind=node.kind,
                state=node.state,
                description=node.description,
                metadata=dict(node.metadata),
                x=_ORIGIN_X,
                y=_ORIGIN_Y + (len(positioned) + index) * _LAYER_Y,
            )
        )

    return WorkflowGraph(
        workflow_id=graph.workflow_id,
        run_id=graph.run_id,
        nodes=positioned,
        edges=list(graph.edges),
    )


__all__ = ["layout_workflow_graph"]
