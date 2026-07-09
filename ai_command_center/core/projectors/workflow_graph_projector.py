"""WorkflowGraphProjector — projects workflow runs and agent pipelines to graphs."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ai_command_center.domain.workflow_graph import GraphEdge, GraphNode, NodeState, WorkflowGraph

_NODE_STATE_VALUES = {state.value for state in NodeState}


def _coerce_node_state(value: str, *, default: NodeState = NodeState.PENDING) -> NodeState:
    text = str(value or "").strip().lower()
    if text in _NODE_STATE_VALUES:
        return NodeState(text)
    return default


def _step_id(step: Mapping[str, Any], index: int) -> str:
    return str(step.get("step_id") or step.get("id") or f"step_{index}")


def _step_label(step: Mapping[str, Any], step_id: str) -> str:
    return str(step.get("name") or step.get("label") or step.get("tool") or step_id)


def _step_kind(step: Mapping[str, Any]) -> str:
    return str(step.get("kind") or step.get("type") or "step")


class WorkflowGraphProjector:
    """Build :class:`WorkflowGraph` instances from bus-fed workflow projections."""

    @staticmethod
    def from_workflow_steps(
        workflow_id: str,
        steps: Sequence[Mapping[str, Any]],
        *,
        run_id: str = "",
        workflow_name: str = "",
        node_states: Mapping[str, str] | None = None,
        active_step_id: str = "",
    ) -> WorkflowGraph:
        """Linearize workflow steps into a graph with optional live state overlay."""
        overlays = dict(node_states or {})
        if active_step_id and active_step_id not in overlays:
            overlays[active_step_id] = NodeState.RUNNING.value

        normalized: list[dict[str, Any]] = []
        for index, raw in enumerate(steps):
            if not isinstance(raw, Mapping):
                continue
            sid = _step_id(raw, index)
            state = overlays.get(sid, str(raw.get("state") or raw.get("status") or "pending"))
            normalized.append(
                {
                    "step_id": sid,
                    "id": sid,
                    "name": _step_label(raw, sid),
                    "kind": _step_kind(raw),
                    "state": state,
                    "description": str(raw.get("description", "")),
                }
            )

        graph = WorkflowGraph.from_workflow_steps(
            workflow_id or "workflow",
            normalized,
            run_id=run_id,
        )
        if workflow_name:
            graph = WorkflowGraph(
                workflow_id=graph.workflow_id,
                run_id=graph.run_id,
                nodes=graph.nodes,
                edges=graph.edges,
            )
        return graph

    @staticmethod
    def from_agent_pipeline(
        pipeline_id: str,
        planned_tools: Sequence[str],
        *,
        stage: str = "",
    ) -> WorkflowGraph:
        """Build a linear graph from agent pipeline planned tools."""
        steps: list[dict[str, Any]] = []
        stage_text = str(stage or "").strip().lower()
        for index, tool in enumerate(planned_tools):
            tool_name = str(tool or "").strip()
            if not tool_name:
                continue
            state = NodeState.PENDING.value
            if stage_text in {"running", "starting"} and index == 0:
                state = NodeState.RUNNING.value
            if stage_text == "complete":
                state = NodeState.COMPLETED.value
            steps.append(
                {
                    "id": f"tool-{index}",
                    "name": tool_name,
                    "kind": "tool",
                    "state": state,
                }
            )
        return WorkflowGraph.from_workflow_steps(
            pipeline_id or "agent-pipeline",
            steps,
            run_id=pipeline_id,
        )

    @staticmethod
    def to_state_items(graph: WorkflowGraph) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Serialize a graph into plain node/edge dicts for AppState reducers."""
        nodes = [
            {
                "node_id": node.node_id,
                "label": node.label,
                "kind": node.kind,
                "state": node.state.value,
                "description": node.description,
                "x": node.x,
                "y": node.y,
            }
            for node in graph.nodes
        ]
        edges = [
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "label": edge.label,
            }
            for edge in graph.edges
        ]
        return nodes, edges

    @staticmethod
    def from_state_items(
        workflow_id: str,
        *,
        run_id: str = "",
        nodes: Sequence[Any],
        edges: Sequence[Any],
    ) -> WorkflowGraph:
        """Rebuild a domain graph from AppState projection items or dicts."""
        domain_nodes: list[GraphNode] = []
        for item in nodes:
            if isinstance(item, Mapping):
                payload = item
            else:
                payload = {
                    "node_id": getattr(item, "node_id", ""),
                    "label": getattr(item, "label", ""),
                    "kind": getattr(item, "kind", "step"),
                    "state": getattr(item, "state", "pending"),
                    "description": getattr(item, "description", ""),
                    "x": getattr(item, "x", 0.0),
                    "y": getattr(item, "y", 0.0),
                }
            domain_nodes.append(
                GraphNode(
                    node_id=str(payload.get("node_id", "")),
                    label=str(payload.get("label", "")),
                    kind=str(payload.get("kind", "step")),
                    state=_coerce_node_state(str(payload.get("state", "pending"))),
                    description=str(payload.get("description", "")),
                    x=float(payload.get("x", 0.0)),
                    y=float(payload.get("y", 0.0)),
                )
            )
        domain_edges: list[GraphEdge] = []
        for item in edges:
            if isinstance(item, Mapping):
                payload = item
            else:
                payload = {
                    "source_id": getattr(item, "source_id", ""),
                    "target_id": getattr(item, "target_id", ""),
                    "label": getattr(item, "label", ""),
                }
            domain_edges.append(
                GraphEdge(
                    source_id=str(payload.get("source_id", "")),
                    target_id=str(payload.get("target_id", "")),
                    label=str(payload.get("label", "")),
                )
            )
        return WorkflowGraph(
            workflow_id=workflow_id,
            run_id=run_id,
            nodes=domain_nodes,
            edges=domain_edges,
        )


__all__ = ["WorkflowGraphProjector"]
