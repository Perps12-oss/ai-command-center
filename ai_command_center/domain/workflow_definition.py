"""Persistable workflow definition (Slice 1b — YAML graph)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import yaml

from ai_command_center.domain.workflow_graph import WorkflowGraph


@dataclass(frozen=True, slots=True)
class WorkflowDefinitionNode:
    node_id: str
    label: str
    kind: str = "step"
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowDefinitionEdge:
    source_id: str
    target_id: str
    label: str = ""
    condition: str = ""


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    workflow_id: str
    workflow_name: str = ""
    nodes: tuple[WorkflowDefinitionNode, ...] = ()
    edges: tuple[WorkflowDefinitionEdge, ...] = ()

    def to_graph(self, *, run_id: str = "", layout: bool = True) -> WorkflowGraph:
        graph = WorkflowGraph.from_definition(
            self.workflow_id,
            nodes=[
                {
                    "node_id": node.node_id,
                    "label": node.label,
                    "kind": node.kind,
                    "description": node.description,
                }
                for node in self.nodes
            ],
            edges=[
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "label": edge.label,
                    "condition": edge.condition,
                }
                for edge in self.edges
            ],
            run_id=run_id,
            layout=layout,
        )
        if self.workflow_name:
            return WorkflowGraph(
                workflow_id=graph.workflow_id,
                run_id=graph.run_id,
                nodes=graph.nodes,
                edges=graph.edges,
            )
        return graph

    def to_yaml(self) -> str:
        payload = {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "nodes": [
                {
                    "id": node.node_id,
                    "label": node.label,
                    "kind": node.kind,
                    "description": node.description,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "label": edge.label,
                    "condition": edge.condition,
                }
                for edge in self.edges
            ],
        }
        return yaml.safe_dump(payload, sort_keys=False)

    @classmethod
    def from_yaml(cls, text: str) -> WorkflowDefinition:
        raw = yaml.safe_load(text) or {}
        if not isinstance(raw, Mapping):
            raise ValueError("workflow YAML must be a mapping")
        workflow_id = str(raw.get("workflow_id") or raw.get("id") or "workflow")
        workflow_name = str(raw.get("workflow_name") or raw.get("name") or "")
        nodes_raw = raw.get("nodes") or []
        edges_raw = raw.get("edges") or []
        nodes: list[WorkflowDefinitionNode] = []
        for index, item in enumerate(nodes_raw):
            if not isinstance(item, Mapping):
                continue
            node_id = str(item.get("id") or item.get("node_id") or f"node_{index}")
            nodes.append(
                WorkflowDefinitionNode(
                    node_id=node_id,
                    label=str(item.get("label") or item.get("name") or node_id),
                    kind=str(item.get("kind") or "step"),
                    description=str(item.get("description") or ""),
                )
            )
        node_ids = {node.node_id for node in nodes}
        edges: list[WorkflowDefinitionEdge] = []
        for item in edges_raw:
            if not isinstance(item, Mapping):
                continue
            source_id = str(item.get("source") or item.get("source_id") or "")
            target_id = str(item.get("target") or item.get("target_id") or "")
            if source_id in node_ids and target_id in node_ids:
                edges.append(
                    WorkflowDefinitionEdge(
                        source_id=source_id,
                        target_id=target_id,
                        label=str(item.get("label") or ""),
                        condition=str(item.get("condition") or ""),
                    )
                )
        return cls(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            nodes=tuple(nodes),
            edges=tuple(edges),
        )

    @classmethod
    def from_steps(cls, workflow_id: str, steps: Sequence[Mapping[str, Any]]) -> WorkflowDefinition:
        """Build a definition from step dicts (linear or depends_on DAG)."""
        graph = WorkflowGraph.from_workflow_steps(workflow_id, [dict(step) for step in steps])
        nodes = tuple(
            WorkflowDefinitionNode(
                node_id=node.node_id,
                label=node.label,
                kind=node.kind,
                description=node.description,
            )
            for node in graph.nodes
        )
        edges = tuple(
            WorkflowDefinitionEdge(
                source_id=edge.source_id,
                target_id=edge.target_id,
                label=edge.label,
                condition=edge.condition,
            )
            for edge in graph.edges
        )
        return cls(workflow_id=workflow_id, nodes=nodes, edges=edges)


__all__ = [
    "WorkflowDefinition",
    "WorkflowDefinitionEdge",
    "WorkflowDefinitionNode",
]
