"""WorkflowGraphProjector tests."""

from __future__ import annotations

from ai_command_center.core.projectors.workflow_graph_projector import WorkflowGraphProjector
from ai_command_center.domain.workflow_graph import NodeState


def test_from_workflow_steps_builds_linear_graph() -> None:
    steps = [
        {"id": "a", "name": "Plan", "state": "pending"},
        {"id": "b", "name": "Run", "state": "pending"},
    ]
    graph = WorkflowGraphProjector.from_workflow_steps("wf-1", steps, run_id="run-1")
    assert graph.workflow_id == "wf-1"
    assert graph.run_id == "run-1"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.nodes[0].label == "Plan"


def test_from_workflow_steps_applies_live_overlay() -> None:
    steps = [
        {"id": "a", "name": "Plan"},
        {"id": "b", "name": "Run"},
    ]
    graph = WorkflowGraphProjector.from_workflow_steps(
        "wf-2",
        steps,
        node_states={"a": NodeState.COMPLETED.value},
        active_step_id="b",
    )
    assert graph.node_by_id("a").state == NodeState.COMPLETED
    assert graph.node_by_id("b").state == NodeState.RUNNING


def test_from_agent_pipeline_builds_tool_nodes() -> None:
    graph = WorkflowGraphProjector.from_agent_pipeline(
        "pipe-1",
        ("search", "summarize"),
        stage="running",
    )
    assert len(graph.nodes) == 2
    assert graph.nodes[0].label == "search"
    assert graph.nodes[0].state == NodeState.RUNNING
