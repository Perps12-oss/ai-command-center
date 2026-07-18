"""GraphCanvas — workflow-domain adapter over the shared BaseGraphCanvas.

Workflow-specific behavior (undo/redo, edge handles, context menus, node
overlays) lives here. Shared zoom/pan/selection/draw lives in
``ui.components.graph``.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_command_center.domain.workflow_graph import GraphEdge, GraphNode, NodeState, WorkflowGraph
from ai_command_center.ui.components.graph import (
    BaseGraphCanvas,
    GraphEdgeVisual,
    GraphNodeVisual,
)
from ai_command_center.ui.components.workflow_node_overlays import node_overlay_kind
from ai_command_center.ui.design_system import theme_v2 as T

_NODE_W = 120
_NODE_H = 48
_EDGE_HANDLE_SIZE = 10

_STATE_COLORS: dict[NodeState, str] = {
    NodeState.PENDING: T.TEXT_MUTED,
    NodeState.RUNNING: T.STATUS_BUSY,
    NodeState.COMPLETED: T.STATUS_READY,
    NodeState.FAILED: T.STATUS_ERROR,
    NodeState.SKIPPED: T.TEXT_MUTED,
    NodeState.WAITING: T.ACCENT_DEFAULT,
    NodeState.CANCELLED: T.TEXT_MUTED,
}

_STATE_FILL: dict[NodeState, str] = {
    NodeState.PENDING: T.BG_GLASS,
    NodeState.RUNNING: T.STATUS_BUSY_BG,
    NodeState.COMPLETED: T.STATUS_READY_BG,
    NodeState.FAILED: T.STATUS_ERROR_BG,
    NodeState.SKIPPED: T.BG_PANEL,
    NodeState.WAITING: T.BG_GLASS,
    NodeState.CANCELLED: T.BG_PANEL,
}


class EditActionType(Enum):
    """Types of graph edit actions for undo/redo."""

    NODE_MOVE = "node_move"
    NODE_ADD = "node_add"
    NODE_DELETE = "node_delete"
    EDGE_ADD = "edge_add"
    EDGE_DELETE = "edge_delete"


@dataclass
class EditAction:
    """Represents a single graph edit action for undo/redo."""

    action_type: EditActionType
    node_id: str = ""
    target_id: str = ""
    old_x: float = 0.0
    old_y: float = 0.0
    new_x: float = 0.0
    new_y: float = 0.0


@dataclass
class GraphHistory:
    """Tracks undo/redo history for graph edits."""

    undo_stack: list[EditAction] = field(default_factory=list)
    redo_stack: list[EditAction] = field(default_factory=list)
    max_size: int = 50

    def push(self, action: EditAction) -> None:
        self.undo_stack.append(action)
        self.redo_stack.clear()
        if len(self.undo_stack) > self.max_size:
            self.undo_stack.pop(0)

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def pop_undo(self) -> EditAction | None:
        if not self.undo_stack:
            return None
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        return action

    def pop_redo(self) -> EditAction | None:
        if not self.redo_stack:
            return None
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        return action


def _workflow_node_visual(node: GraphNode) -> GraphNodeVisual:
    color = _STATE_COLORS.get(node.state, T.TEXT_MUTED)
    fill = _STATE_FILL.get(node.state, T.BG_GLASS)
    badge = ""
    badge_color = ""
    overlay = node_overlay_kind(node)
    if overlay == "approval":
        badge = "✓"
        badge_color = T.ACCENT_DEFAULT
    elif overlay == "retry":
        badge = "↻"
        badge_color = T.STATUS_BUSY
    return GraphNodeVisual(
        node_id=node.node_id,
        x=node.x,
        y=node.y,
        label=node.label[:16],
        width=_NODE_W,
        height=_NODE_H,
        shape="rect",
        fill=fill,
        outline=color,
        outline_width=1,
        text_color=T.TEXT_PRIMARY,
        font_size=10,
        status_dot_color=color,
        badge=badge,
        badge_color=badge_color,
    )


def _workflow_edge_visual(edge: GraphEdge) -> GraphEdgeVisual:
    return GraphEdgeVisual(
        edge_id=GraphEdgeVisual.make_id(edge.source_id, edge.target_id),
        source_id=edge.source_id,
        target_id=edge.target_id,
        color=T.BG_GLASS_BORDER,
        width=2,
        arrow="forward",
    )


class GraphCanvas(BaseGraphCanvas):
    """Workflow graph adapter: projects WorkflowGraph onto BaseGraphCanvas."""

    def __init__(
        self,
        master: Any,
        *,
        on_node_select: Callable[[GraphNode], None] | None = None,
        on_node_move: Callable[[str, float, float], None] | None = None,
        on_edge_create: Callable[[str, str], None] | None = None,
        on_edge_delete: Callable[[GraphEdge], None] | None = None,
        on_node_add: Callable[[str, float, float], None] | None = None,
        on_undo: Callable[[], None] | None = None,
        on_redo: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        self._on_workflow_node_select = on_node_select or (lambda _node: None)
        self._on_workflow_node_move = on_node_move or (lambda _nid, _x, _y: None)
        self._on_edge_create = on_edge_create or (lambda _src, _tgt: None)
        self._on_edge_delete = on_edge_delete or (lambda _edge: None)
        self._on_node_add = on_node_add or (lambda _node_type, _x, _y: None)
        self._on_undo = on_undo or (lambda: None)
        self._on_redo = on_redo or (lambda: None)

        self._graph: WorkflowGraph | None = None
        self._history = GraphHistory()
        self._edge_draw_start: tuple[float, float] | None = None
        self._edge_draw_source_id = ""
        self._context_menu: tk.Menu | None = None
        self._move_origins: dict[str, tuple[float, float]] = {}

        super().__init__(
            master,
            on_node_select=self._forward_node_select,
            on_node_move=self._forward_node_move,
            enable_zoom=True,
            enable_pan=True,
            enable_multi_select=True,
            enable_node_drag=True,
            enable_selection_box=True,
            show_scrollbars=True,
            empty_message="No nodes",
            **kwargs,
        )

        self.tk_canvas.bind("<Button-3>", self._on_canvas_context)
        self.tk_canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.tk_canvas.bind("<Key>", self._on_key_press)
        self.tk_canvas.focus_set()

    def _on_canvas_drag(self, event: tk.Event) -> None:
        super()._on_canvas_drag(event)
        # Keep WorkflowGraph domain coordinates in sync while dragging.
        if self._drag_node_id and self._graph is not None:
            visual = self._node_index.get(self._drag_node_id)
            domain = self._graph.node_by_id(self._drag_node_id)
            if visual is not None and domain is not None:
                domain.x = visual.x
                domain.y = visual.y

    def render(
        self,
        graph: WorkflowGraph,
        *,
        selected_node_ids: set[str] | None = None,
        selected_edge_ids: set[str] | None = None,
    ) -> None:
        self._graph = graph
        nodes = [_workflow_node_visual(n) for n in graph.nodes]
        edges = [_workflow_edge_visual(e) for e in graph.edges]
        self.set_scene(
            nodes,
            edges,
            selected_node_ids=selected_node_ids,
            selected_edge_ids=selected_edge_ids,
        )

    def _forward_node_select(self, node_id: str) -> None:
        if self._graph is None:
            return
        node = self._graph.node_by_id(node_id)
        if node is not None:
            self._on_workflow_node_select(node)

    def _forward_node_move(self, node_id: str, x: float, y: float) -> None:
        if self._graph is None:
            return
        node = self._graph.node_by_id(node_id)
        if node is None:
            return
        old = self._move_origins.pop(node_id, (node.x, node.y))
        node.x = x
        node.y = y
        self._history.push(
            EditAction(
                action_type=EditActionType.NODE_MOVE,
                node_id=node_id,
                old_x=old[0],
                old_y=old[1],
                new_x=x,
                new_y=y,
            )
        )
        self._on_workflow_node_move(node_id, x, y)

    def _decorate_node(self, node: GraphNodeVisual, tags: tuple[str, ...]) -> None:
        handle_x = node.x + node.width
        handle_y = node.y + node.height / 2
        self.tk_canvas.create_oval(
            handle_x - _EDGE_HANDLE_SIZE / 2,
            handle_y - _EDGE_HANDLE_SIZE / 2,
            handle_x + _EDGE_HANDLE_SIZE / 2,
            handle_y + _EDGE_HANDLE_SIZE / 2,
            fill=T.ACCENT_DEFAULT,
            outline="",
            tags=("edge_handle", "edge_handle_" + node.node_id),
        )

    def _hit_test_edge_handle(self, canvas_x: float, canvas_y: float) -> str | None:
        if self._graph is None:
            return None
        for node in self._graph.nodes:
            hx = node.x + _NODE_W
            hy = node.y + _NODE_H / 2
            dist = ((canvas_x - hx) ** 2 + (canvas_y - hy) ** 2) ** 0.5
            if dist <= _EDGE_HANDLE_SIZE:
                return node.node_id
        return None

    def _intercept_press(self, canvas_x: float, canvas_y: float, event: tk.Event) -> bool:
        handle_node_id = self._hit_test_edge_handle(canvas_x, canvas_y)
        if handle_node_id:
            self._edge_draw_start = (canvas_x, canvas_y)
            self._edge_draw_source_id = handle_node_id
            self.selection.clear()
            return True

        # Complete pending edge when clicking a target node
        if self._edge_draw_source_id:
            visual = self.hit_test_node(canvas_x, canvas_y)
            if visual is not None and visual.node_id != self._edge_draw_source_id:
                self._on_edge_create(self._edge_draw_source_id, visual.node_id)
                self._edge_draw_start = None
                self._edge_draw_source_id = ""
                return True

        # Sync domain node positions when drag starts
        visual = self.hit_test_node(canvas_x, canvas_y)
        if visual is not None and self._graph is not None:
            domain = self._graph.node_by_id(visual.node_id)
            if domain is not None:
                self._move_origins[visual.node_id] = (domain.x, domain.y)
        return False

    def _intercept_release(self, canvas_x: float, canvas_y: float, event: tk.Event) -> bool:
        if self._edge_draw_start is not None:
            self._edge_draw_start = None
            self._edge_draw_source_id = ""
            return True
        return False

    def _on_canvas_context(self, event: tk.Event) -> None:
        if self._context_menu:
            self._context_menu.destroy()
        canvas_x, canvas_y = self._event_xy(event)
        visual = self.hit_test_node(canvas_x, canvas_y)
        edge_visual = self.hit_test_edge(canvas_x, canvas_y)
        if visual is None and edge_visual is None:
            return

        self._context_menu = tk.Menu(self.tk_canvas, tearoff=0)
        if visual is not None and self._graph is not None:
            node = self._graph.node_by_id(visual.node_id)
            if node is not None:
                self._context_menu.add_command(
                    label=f"Edit '{node.label[:12]}'...",
                    command=lambda n=node: self._on_workflow_node_select(n),
                )
                self._context_menu.add_separator()
        if edge_visual is not None:
            self._context_menu.add_command(
                label="Delete Edge",
                command=lambda e=edge_visual: self._delete_edge(e.source_id, e.target_id),
            )
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _on_canvas_double_click(self, event: tk.Event) -> None:
        canvas_x, canvas_y = self._event_xy(event)
        edge_visual = self.hit_test_edge(canvas_x, canvas_y)
        if edge_visual is not None:
            self._delete_edge(edge_visual.source_id, edge_visual.target_id)

    def _delete_edge(self, source_id: str, target_id: str) -> None:
        if self._graph is None:
            return
        for edge in self._graph.edges:
            if edge.source_id == source_id and edge.target_id == target_id:
                self.selection.selected_edge_ids.discard(
                    GraphEdgeVisual.make_id(source_id, target_id)
                )
                self._on_edge_delete(edge)
                break

    def _on_key_press(self, event: tk.Event) -> None:
        if self._graph is None:
            return
        if event.state & 0x4 and event.keysym == "z":
            self._handle_undo()
        elif event.state & 0x4 and (
            event.keysym == "y" or (event.keysym == "Z" and event.state & 0x1)
        ):
            self._handle_redo()
        elif event.state & 0x4 and event.keysym == "a":
            self.selection.select_nodes({n.node_id for n in self._graph.nodes})
            self.render(self._graph, selected_node_ids=self.selection.copy_node_ids())
        elif event.keysym in ("Delete", "BackSpace"):
            self._delete_selected()
        elif event.keysym == "Escape":
            self.selection.clear()
            self.render(self._graph)

    def _handle_undo(self) -> None:
        action = self._history.pop_undo()
        if action is None:
            return
        self._on_undo()

    def _handle_redo(self) -> None:
        action = self._history.pop_redo()
        if action is None:
            return
        self._on_redo()

    def _delete_selected(self) -> None:
        if self._graph is None:
            return
        for edge_id in list(self.selection.selected_edge_ids):
            parts = edge_id.split("->")
            if len(parts) == 2:
                self._delete_edge(parts[0], parts[1])
        self.selection.clear()

    def can_undo(self) -> bool:
        return self._history.can_undo()

    def can_redo(self) -> bool:
        return self._history.can_redo()

    def record_node_move(self, node_id: str, old_x: float, old_y: float) -> None:
        self._history.push(
            EditAction(
                action_type=EditActionType.NODE_MOVE,
                node_id=node_id,
                old_x=old_x,
                old_y=old_y,
            )
        )


__all__ = ["GraphCanvas", "EditAction", "EditActionType", "GraphHistory"]
