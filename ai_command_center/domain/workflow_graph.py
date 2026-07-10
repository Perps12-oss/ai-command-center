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
    def from_definition(
        cls,
        workflow_id: str,
        *,
        nodes: list[dict] | list[GraphNode],
        edges: list[dict] | list[GraphEdge],
        run_id: str = "",
        layout: bool = True,
    ) -> "WorkflowGraph":
        """Build a graph from explicit node and edge definitions (DAG-safe)."""
        domain_nodes: list[GraphNode] = []
        for index, raw in enumerate(nodes):
            if isinstance(raw, GraphNode):
                domain_nodes.append(raw)
                continue
            node_id = str(raw.get("node_id") or raw.get("id") or f"node_{index}")
            state_str = str(raw.get("state", raw.get("status", "pending")))
            try:
                state = NodeState(state_str)
            except ValueError:
                state = NodeState.PENDING
            domain_nodes.append(
                GraphNode(
                    node_id=node_id,
                    label=str(raw.get("label") or raw.get("name") or node_id),
                    kind=str(raw.get("kind") or "step"),
                    state=state,
                    description=str(raw.get("description", "")),
                    metadata=dict(raw.get("metadata") or {}),
                    x=float(raw.get("x", 0.0)),
                    y=float(raw.get("y", 0.0)),
                )
            )

        node_ids = {node.node_id for node in domain_nodes}
        domain_edges: list[GraphEdge] = []
        for raw in edges:
            if isinstance(raw, GraphEdge):
                if raw.source_id in node_ids and raw.target_id in node_ids:
                    domain_edges.append(raw)
                continue
            source_id = str(raw.get("source_id") or raw.get("source") or "")
            target_id = str(raw.get("target_id") or raw.get("target") or "")
            if source_id in node_ids and target_id in node_ids:
                domain_edges.append(
                    GraphEdge(
                        source_id=source_id,
                        target_id=target_id,
                        label=str(raw.get("label", "")),
                        condition=str(raw.get("condition", "")),
                    )
                )

        graph = cls(
            workflow_id=workflow_id,
            run_id=run_id,
            nodes=domain_nodes,
            edges=domain_edges,
        )
        if layout and graph.nodes and all(node.x == 0.0 and node.y == 0.0 for node in graph.nodes):
            from ai_command_center.core.workflow.workflow_graph_layout import layout_workflow_graph

            return layout_workflow_graph(graph)
        return graph

    @classmethod
    def _from_steps_dag(
        cls,
        workflow_id: str,
        steps: list[dict],
        run_id: str = "",
    ) -> "WorkflowGraph":
        """Build a DAG from steps using depends_on / next fields."""
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        id_by_step: dict[int, str] = {}

        for index, step in enumerate(steps):
            sid = str(step.get("step_id", step.get("id", f"step_{index}")))
            id_by_step[index] = sid
            state_str = str(step.get("state", step.get("status", "pending")))
            try:
                state = NodeState(state_str)
            except ValueError:
                state = NodeState.PENDING
            nodes.append(
                GraphNode(
                    node_id=sid,
                    label=str(step.get("name", sid)),
                    kind=str(step.get("kind", "step")),
                    state=state,
                    description=str(step.get("description", "")),
                )
            )

        node_ids = {node.node_id for node in nodes}
        for index, step in enumerate(steps):
            sid = id_by_step[index]
            depends_on = step.get("depends_on") or step.get("depends") or []
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            for dep in depends_on:
                dep_id = str(dep)
                if dep_id in node_ids:
                    edges.append(GraphEdge(source_id=dep_id, target_id=sid))
            next_ids = step.get("next") or []
            if isinstance(next_ids, str):
                next_ids = [next_ids]
            for nxt in next_ids:
                target_id = str(nxt)
                if target_id in node_ids:
                    edges.append(GraphEdge(source_id=sid, target_id=target_id))

        if not edges:
            for index in range(1, len(nodes)):
                edges.append(
                    GraphEdge(
                        source_id=nodes[index - 1].node_id,
                        target_id=nodes[index].node_id,
                    )
                )

        graph = cls(workflow_id=workflow_id, run_id=run_id, nodes=nodes, edges=edges)
        from ai_command_center.core.workflow.workflow_graph_layout import layout_workflow_graph

        return layout_workflow_graph(graph)

    @classmethod
    def from_workflow_steps(
        cls,
        workflow_id: str,
        steps: list[dict],
        run_id: str = "",
    ) -> "WorkflowGraph":
        """Build a graph from step dicts (linear list or DAG via depends_on/next)."""
        if isinstance(steps, dict):
            return cls.from_definition(
                workflow_id,
                nodes=list(steps.get("nodes") or []),
                edges=list(steps.get("edges") or []),
                run_id=run_id,
            )

        has_dag_hints = any(
            isinstance(step, dict) and (step.get("depends_on") or step.get("next"))
            for step in steps
        )
        if has_dag_hints:
            return cls._from_steps_dag(workflow_id, steps, run_id=run_id)

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
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
