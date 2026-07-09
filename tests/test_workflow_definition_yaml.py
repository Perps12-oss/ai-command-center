"""WorkflowDefinition YAML round-trip tests."""

from __future__ import annotations

from ai_command_center.domain.workflow_definition import (
    WorkflowDefinition,
    WorkflowDefinitionEdge,
    WorkflowDefinitionNode,
)


def test_workflow_definition_yaml_roundtrip() -> None:
    definition = WorkflowDefinition(
        workflow_id="demo-dag",
        workflow_name="Demo DAG",
        nodes=(
            WorkflowDefinitionNode("start", "Start", kind="start"),
            WorkflowDefinitionNode("approve", "Approve", kind="approval"),
            WorkflowDefinitionNode("retry", "Retry Step", kind="retry"),
            WorkflowDefinitionNode("end", "End", kind="end"),
        ),
        edges=(
            WorkflowDefinitionEdge("start", "approve"),
            WorkflowDefinitionEdge("approve", "retry"),
            WorkflowDefinitionEdge("retry", "end"),
        ),
    )
    text = definition.to_yaml()
    loaded = WorkflowDefinition.from_yaml(text)
    assert loaded.workflow_id == "demo-dag"
    assert loaded.workflow_name == "Demo DAG"
    assert len(loaded.nodes) == 4
    assert len(loaded.edges) == 3

    graph = loaded.to_graph()
    assert len(graph.nodes) == 4
    approve = graph.node_by_id("approve")
    assert approve is not None
    assert approve.kind == "approval"


def test_workflow_definition_from_steps() -> None:
    steps = [
        {"id": "a", "name": "A"},
        {"id": "b", "name": "B", "depends_on": ["a"]},
    ]
    definition = WorkflowDefinition.from_steps("linear", steps)
    assert len(definition.nodes) == 2
    assert len(definition.edges) == 1
