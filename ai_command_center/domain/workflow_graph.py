"""WorkflowGraph domain model — directed graph of workflow nodes.

Used by WorkflowGraphView to render visual workflow diagrams.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NodeState(str, Enum):
    """Visual state of a workflow graph node."""

    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    WAITING   = "waiting"    # waiting for approval
    CANCELLED = "cancelled"


@dataclass
class GraphNode:
    """A single node in the workflow graph."""

    node_id: str = ""
    label: str = ""
    kind: str = "step"              # "step" | "decision" | "approval" | "start" | "end"
    state: NodeState = NodeState.PENDING
    description: str = ""
    metadata: dict = field(default_factory=dict)
    # Computed layout position (pixels from top-left of canvas)
    x: float = 0.0
    y: float = 0.0


@dataclass
class GraphEdge:
    """A directed edge between two nodes."""

    source_id: str = ""
    target_id: str = ""
    label: str = ""
    condition: str = ""             # optional conditional expression


@dataclass
class WorkflowGraph:
    """Complete workflow graph — nodes + edges."""

    workflow_id: str = ""
    run_id: str = ""
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def node_by_id(self, node_id: str) -> GraphNode | None:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def successors(self, node_id: str) -> list[GraphNode]:
        target_ids = {e.target_id for e in self.edges if e.source_id == node_id}
        return [n for n in self.nodes if n.node_id in target_ids]

    def predecessors(self, node_id: str) -> list[GraphNode]:
        source_ids = {e.source_id for e in self.edges if e.target_id == node_id}
        return [n for n in self.nodes if n.node_id in source_ids]

    @classmethod
    def from_workflow_steps(
        cls,
        workflow_id: str,
        steps: list[dict],
        run_id: str = "",
    ) -> "WorkflowGraph":
        """Build a linear graph from a flat list of step dicts."""
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        for i, step in enumerate(steps):
            sid = str(step.get("step_id", step.get("id", f"step_{i}")))
            state_str = str(step.get("state", step.get("status", "pending")))
            try:
                state = NodeState(state_str)
            except ValueError:
                state = NodeState.PENDING

            nodes.append(GraphNode(
                node_id=sid,
                label=str(step.get("name", sid)),
                kind=str(step.get("kind", "step")),
                state=state,
                description=str(step.get("description", "")),
                x=float(i) * 160 + 40,
                y=80,
            ))
            if i > 0:
                edges.append(GraphEdge(
                    source_id=nodes[i - 1].node_id,
                    target_id=sid,
                ))

        return cls(workflow_id=workflow_id, run_id=run_id, nodes=nodes, edges=edges)
