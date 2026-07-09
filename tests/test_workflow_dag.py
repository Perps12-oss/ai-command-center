"""Workflow DAG graph builder tests."""

from __future__ import annotations

from ai_command_center.core.projectors.workflow_graph_projector import WorkflowGraphProjector
from ai_command_center.domain.workflow_graph import WorkflowGraph


def test_workflow_graph_dag_from_depends_on() -> None:
    steps = [
        {"id": "start", "name": "Start"},
        {"id": "branch_a", "name": "Branch A", "depends_on": ["start"]},
        {"id": "branch_b", "name": "Branch B", "depends_on": ["start"]},
        {"id": "join", "name": "Join", "depends_on": ["branch_a", "branch_b"]},
    ]
    graph = WorkflowGraph.from_workflow_steps("fork-join", steps)
    assert len(graph.nodes) == 4
    assert len(graph.edges) == 4
    join = graph.node_by_id("join")
    assert join is not None
    preds = {node.node_id for node in graph.predecessors("join")}
    assert preds == {"branch_a", "branch_b"}


def test_workflow_graph_dag_from_next() -> None:
    steps = [
        {"id": "a", "name": "A", "next": ["b", "c"]},
        {"id": "b", "name": "B"},
        {"id": "c", "name": "C"},
    ]
    graph = WorkflowGraph.from_workflow_steps("branch", steps)
    successors = {node.node_id for node in graph.successors("a")}
    assert successors == {"b", "c"}


def test_projector_preserves_dag_hints() -> None:
    steps = [
        {"id": "root", "name": "Root"},
        {"id": "left", "name": "Left", "depends_on": ["root"]},
        {"id": "right", "name": "Right", "depends_on": ["root"]},
    ]
    graph = WorkflowGraphProjector.from_workflow_steps("wf", steps)
    assert len(graph.edges) == 2
    assert graph.nodes[0].x != graph.nodes[-1].x or graph.nodes[0].y != graph.nodes[-1].y
