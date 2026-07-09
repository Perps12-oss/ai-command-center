"""Workflow graph AppState slice (ACC UI Refurbishment PR 12–13)."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Mapping

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    AGENT_PIPELINE_PLANNED,
    AGENT_PIPELINE_STAGE,
    AGENT_PIPELINE_STARTED,
    UI_WORKFLOW_NODE_SELECT,
    UI_WORKFLOW_NODE_MOVE,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)
from ai_command_center.core.projectors.workflow_graph_projector import WorkflowGraphProjector
from ai_command_center.domain.workflow_graph import NodeState, WorkflowGraph

_MAX_STORED_STEPS = 32


@dataclass(frozen=True, slots=True)
class WorkflowGraphNodeItem:
    node_id: str = ""
    label: str = ""
    kind: str = "step"
    state: str = NodeState.PENDING.value
    description: str = ""
    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True, slots=True)
class WorkflowGraphEdgeItem:
    source_id: str = ""
    target_id: str = ""
    label: str = ""


@dataclass(frozen=True, slots=True)
class WorkflowGraphState:
    """Active workflow graph projection for the workflow workspace."""

    workflow_id: str = ""
    run_id: str = ""
    workflow_name: str = "Workflow"
    nodes: tuple[WorkflowGraphNodeItem, ...] = ()
    edges: tuple[WorkflowGraphEdgeItem, ...] = ()
    selected_node_id: str = ""
    revision: int = 0
    running: bool = False
    step_payload_json: str = ""


def _encode_steps(steps: list[dict[str, Any]]) -> str:
    trimmed = steps[:_MAX_STORED_STEPS]
    return json.dumps(trimmed, separators=(",", ":"), sort_keys=True)


def decode_workflow_steps(payload_json: str) -> list[dict[str, Any]]:
    """Decode stored workflow step JSON from :class:`WorkflowGraphState`."""
    return _decode_steps(payload_json)


def seed_demo_workflow_graph() -> WorkflowGraphState:
    """Default workflow graph with the demo-linear catalog flow."""
    from ai_command_center.core.projectors.automation_workspace_projector import (
        AutomationWorkspaceProjector,
    )

    workflow_id = "demo-linear"
    steps = AutomationWorkspaceProjector.steps_for_workflow(workflow_id)
    return _project_steps(
        WorkflowGraphState(),
        steps,
        workflow_id=workflow_id,
        run_id="",
        workflow_name="Demo Linear Flow",
        running=False,
    )


def _decode_steps(payload_json: str) -> list[dict[str, Any]]:
    if not payload_json:
        return []
    try:
        raw = json.loads(payload_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _overlay_from_nodes(nodes: tuple[WorkflowGraphNodeItem, ...]) -> dict[str, str]:
    return {node.node_id: node.state for node in nodes if node.node_id}


def _apply_overlay(
    nodes: tuple[WorkflowGraphNodeItem, ...],
    node_id: str,
    state: str,
) -> tuple[WorkflowGraphNodeItem, ...]:
    if not node_id:
        return nodes
    updated: list[WorkflowGraphNodeItem] = []
    changed = False
    for node in nodes:
        if node.node_id == node_id and node.state != state:
            updated.append(replace(node, state=state))
            changed = True
        else:
            updated.append(node)
    return tuple(updated) if changed else nodes


def _items_from_graph(
    graph: WorkflowGraph,
) -> tuple[tuple[WorkflowGraphNodeItem, ...], tuple[WorkflowGraphEdgeItem, ...]]:
    raw_nodes, raw_edges = WorkflowGraphProjector.to_state_items(graph)
    nodes = tuple(WorkflowGraphNodeItem(**entry) for entry in raw_nodes)
    edges = tuple(WorkflowGraphEdgeItem(**entry) for entry in raw_edges)
    return nodes, edges


def _project_steps(
    state: WorkflowGraphState,
    steps: list[dict[str, Any]],
    *,
    workflow_id: str,
    run_id: str,
    workflow_name: str,
    running: bool,
    overlays: Mapping[str, str] | None = None,
    active_step_id: str = "",
) -> WorkflowGraphState:
    graph = WorkflowGraphProjector.from_workflow_steps(
        workflow_id,
        steps,
        run_id=run_id,
        workflow_name=workflow_name,
        node_states=overlays,
        active_step_id=active_step_id,
    )
    nodes, edges = _items_from_graph(graph)
    return replace(
        state,
        workflow_id=workflow_id,
        run_id=run_id,
        workflow_name=workflow_name or state.workflow_name,
        nodes=nodes,
        edges=edges,
        running=running,
        step_payload_json=_encode_steps(steps),
        revision=state.revision + 1,
    )


def reduce_workflow_graph_state(state: WorkflowGraphState, event: Event) -> WorkflowGraphState:
    """Pure reducer for workflow graph projections and selection."""
    if event.topic == WORKFLOW_STARTED:
        payload = dict(event.payload or {})
        workflow_id = str(payload.get("workflow_id") or "workflow")
        run_id = str(payload.get("run_id") or "")
        steps = [dict(step) for step in payload.get("steps") or [] if isinstance(step, Mapping)]
        if not steps:
            return state
        return _project_steps(
            state,
            steps,
            workflow_id=workflow_id,
            run_id=run_id,
            workflow_name=workflow_id.replace("-", " ").title(),
            running=True,
        )

    if event.topic == WORKFLOW_STEP_STARTED:
        step_id = str(event.payload.get("step_id") or "")
        run_id = str(event.payload.get("run_id") or "")
        if run_id and state.run_id and run_id != state.run_id:
            return state
        nodes = _apply_overlay(state.nodes, step_id, NodeState.RUNNING.value)
        if nodes == state.nodes:
            return state
        return replace(state, nodes=nodes, revision=state.revision + 1, running=True)

    if event.topic == WORKFLOW_STEP_COMPLETED:
        step_id = str(event.payload.get("step_id") or "")
        run_id = str(event.payload.get("run_id") or "")
        if run_id and state.run_id and run_id != state.run_id:
            return state
        success = bool(event.payload.get("success", True))
        next_state = NodeState.COMPLETED.value if success else NodeState.FAILED.value
        nodes = _apply_overlay(state.nodes, step_id, next_state)
        if nodes == state.nodes:
            return state
        return replace(state, nodes=nodes, revision=state.revision + 1, running=True)

    if event.topic in {WORKFLOW_COMPLETED, WORKFLOW_FAILED}:
        run_id = str(event.payload.get("run_id") or "")
        if run_id and state.run_id and run_id != state.run_id:
            return state
        final_state = (
            NodeState.COMPLETED.value
            if event.topic == WORKFLOW_COMPLETED
            else NodeState.FAILED.value
        )
        nodes = tuple(
            replace(
                node,
                state=final_state
                if node.state in {NodeState.RUNNING.value, NodeState.PENDING.value}
                else node.state,
            )
            for node in state.nodes
        )
        return replace(state, nodes=nodes, running=False, revision=state.revision + 1)

    if event.topic == AGENT_PIPELINE_STARTED:
        pipeline_id = str(event.payload.get("pipeline_id") or "agent-pipeline")
        graph = WorkflowGraphProjector.from_agent_pipeline(pipeline_id, (), stage="starting")
        nodes, edges = _items_from_graph(graph)
        return replace(
            state,
            workflow_id=pipeline_id,
            run_id=pipeline_id,
            workflow_name="Agent Pipeline",
            nodes=nodes,
            edges=edges,
            running=True,
            revision=state.revision + 1,
        )

    if event.topic == AGENT_PIPELINE_PLANNED:
        pipeline_id = str(event.payload.get("pipeline_id") or state.workflow_id or "agent-pipeline")
        tools = tuple(str(tool) for tool in event.payload.get("planned_tools") or ())
        graph = WorkflowGraphProjector.from_agent_pipeline(
            pipeline_id,
            tools,
            stage="running" if state.running else "planned",
        )
        nodes, edges = _items_from_graph(graph)
        return replace(
            state,
            workflow_id=pipeline_id,
            run_id=pipeline_id,
            workflow_name="Agent Pipeline",
            nodes=nodes,
            edges=edges,
            revision=state.revision + 1,
        )

    if event.topic == AGENT_PIPELINE_STAGE:
        pipeline_id = str(event.payload.get("pipeline_id") or state.workflow_id or "agent-pipeline")
        stage = str(event.payload.get("stage") or "")
        steps = _decode_steps(state.step_payload_json)
        if steps:
            return _project_steps(
                state,
                steps,
                workflow_id=pipeline_id,
                run_id=state.run_id or pipeline_id,
                workflow_name=state.workflow_name,
                running=stage not in {"complete", "failed", ""},
                overlays=_overlay_from_nodes(state.nodes),
            )
        tools = [node.label for node in state.nodes]
        graph = WorkflowGraphProjector.from_agent_pipeline(pipeline_id, tools, stage=stage)
        nodes, edges = _items_from_graph(graph)
        return replace(
            state,
            workflow_id=pipeline_id,
            nodes=nodes,
            edges=edges,
            running=stage not in {"complete", "failed", ""},
            revision=state.revision + 1,
        )

    if event.topic == UI_WORKFLOW_NODE_SELECT:
        node_id = str(event.payload.get("node_id") or "")
        if not node_id or node_id == state.selected_node_id:
            return state
        return replace(
            state,
            selected_node_id=node_id,
            revision=state.revision + 1,
        )

    if event.topic == UI_WORKFLOW_NODE_MOVE:
        node_id = str(event.payload.get("node_id") or "")
        if not node_id:
            return state
        x = float(event.payload.get("x", 0.0))
        y = float(event.payload.get("y", 0.0))
        nodes = tuple(
            replace(node, x=x, y=y) if node.node_id == node_id else node
            for node in state.nodes
        )
        if nodes == state.nodes:
            return state
        return replace(state, nodes=nodes, revision=state.revision + 1)

    return state


__all__ = [
    "WorkflowGraphEdgeItem",
    "WorkflowGraphNodeItem",
    "WorkflowGraphState",
    "decode_workflow_steps",
    "reduce_workflow_graph_state",
    "seed_demo_workflow_graph",
]
