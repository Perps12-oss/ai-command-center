"""GraphCanvas — tkinter canvas renderer for workflow graphs.

P4 Features (2026-07-10):
- P4.2: Canvas zoom/pan with mouse wheel and drag
- P4.4: Multi-select with Ctrl+click and selection box
- P4.5: Undo/redo for graph edits
- P4.6: Keyboard shortcuts
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.workflow_graph import GraphEdge, GraphNode, NodeState, WorkflowGraph
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
    target_id: str = ""  # For edge operations
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


class GraphCanvas(ctk.CTkFrame):
    """Canvas-based workflow graph renderer with node hit-testing, edge management, zoom/pan, multi-select, and undo/redo."""

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
        super().__init__(master, fg_color=T.BG_DEEP, corner_radius=0, **kwargs)
        self._on_node_select = on_node_select or (lambda _node: None)
        self._on_node_move = on_node_move or (lambda _node_id, _x, _y: None)
        self._on_edge_create = on_edge_create or (lambda _src, _tgt: None)
        self._on_edge_delete = on_edge_delete or (lambda _edge: None)
        self._on_node_add = on_node_add or (lambda _node_type, _x, _y: None)
        self._on_undo = on_undo or (lambda: None)
        self._on_redo = on_redo or (lambda: None)

        self._graph: WorkflowGraph | None = None
        self._selected_node_ids: set[str] = set()
        self._selected_edge_ids: set[str] = set()
        self._node_bounds: dict[str, tuple[float, float, float, float]] = {}
        self._edge_bounds: dict[tuple[str, str], tuple[float, float, float, float]] = {}
        self._drag_node_id = ""
        self._drag_offset: tuple[float, float] = (0.0, 0.0)
        self._edge_draw_start: tuple[float, float] | None = None
        self._edge_draw_source_id = ""
        self._history = GraphHistory()

        # Zoom/Pan state
        self._zoom_level = 1.0
        self._zoom_min = 0.25
        self._zoom_max = 3.0
        self._zoom_step = 0.1
        self._pan_start: tuple[float, float] | None = None
        self._pan_mode = False  # Middle mouse button

        # Selection box for multi-select
        self._selection_start: tuple[float, float] | None = None
        self._selection_box: int | None = None

        self._canvas = tk.Canvas(self, bg=T.BG_DEEP, highlightthickness=0)
        h_scroll = tk.Scrollbar(self, orient="horizontal", command=self._canvas.xview)
        v_scroll = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        # Mouse bindings
        self._canvas.bind("<Button-1>", self._on_canvas_press)
        self._canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self._canvas.bind("<Button-3>", self._on_canvas_context)
        self._canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self._canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self._canvas.bind("<Button-2>", self._on_pan_start)
        self._canvas.bind("<B2-Motion>", self._on_pan_drag)
        self._canvas.bind("<ButtonRelease-2>", self._on_pan_end)
        self._canvas.bind("<Shift-Button-1>", self._on_selection_start)

        # Keyboard bindings on canvas (canvas must have focus)
        self._canvas.bind("<Key>", self._on_key_press)
        self._canvas.bind("<FocusIn>", self._on_focus_in)
        self._canvas.focus_set()  # Allow canvas to receive keyboard events

        self._context_menu: tk.Menu | None = None

    def render(
        self,
        graph: WorkflowGraph,
        *,
        selected_node_ids: set[str] | None = None,
        selected_edge_ids: set[str] | None = None,
    ) -> None:
        self._graph = graph
        if selected_node_ids is not None:
            self._selected_node_ids = selected_node_ids
        if selected_edge_ids is not None:
            self._selected_edge_ids = selected_edge_ids
        self._node_bounds.clear()
        self._edge_bounds.clear()
        self._canvas.delete("all")

        # Apply zoom transform
        self._canvas.scale("all", 0, 0, self._zoom_level, self._zoom_level)

        if not graph.nodes:
            self._canvas.create_text(
                100,
                60,
                text="No nodes",
                fill=T.TEXT_MUTED,
                font=(T.FONT_FAMILY, 12),
            )
            return

        # Draw edges first (below nodes)
        for edge in graph.edges:
            self._draw_edge(edge)

        # Draw nodes on top
        for node in graph.nodes:
            self._draw_node(node)

        max_x = max((n.x + _NODE_W + 40) for n in graph.nodes)
        max_y = max((n.y + _NODE_H + 40) for n in graph.nodes)
        self._canvas.configure(scrollregion=(0, 0, max_x * self._zoom_level, max_y * self._zoom_level))

    def _draw_node(self, node: GraphNode) -> None:
        x, y = node.x, node.y
        color = _STATE_COLORS.get(node.state, T.TEXT_MUTED)
        fill = _STATE_FILL.get(node.state, T.BG_GLASS)
        is_selected = node.node_id in self._selected_node_ids
        outline = T.ACCENT_DEFAULT if is_selected else color
        width = 2 if is_selected else 1

        self._node_bounds[node.node_id] = (x, y, x + _NODE_W, y + _NODE_H)
        self._canvas.create_rectangle(
            x,
            y,
            x + _NODE_W,
            y + _NODE_H,
            fill=fill,
            outline=outline,
            width=width,
            tags=("node", node.node_id),
        )
        self._canvas.create_oval(
            x + 8,
            y + _NODE_H / 2 - 5,
            x + 18,
            y + _NODE_H / 2 + 5,
            fill=color,
            outline="",
            tags=("node", node.node_id),
        )
        self._canvas.create_text(
            x + _NODE_W / 2 + 5,
            y + _NODE_H / 2,
            text=node.label[:16],
            fill=T.TEXT_PRIMARY,
            font=(T.FONT_FAMILY, 10),
            anchor="center",
            tags=("node", node.node_id),
        )
        overlay = node_overlay_kind(node)
        if overlay == "approval":
            self._canvas.create_text(
                x + _NODE_W - 10,
                y + 8,
                text="✓",
                fill=T.ACCENT_DEFAULT,
                font=(T.FONT_FAMILY, 10, "bold"),
                tags=("node", node.node_id),
            )
        elif overlay == "retry":
            self._canvas.create_text(
                x + _NODE_W - 12,
                y + 8,
                text="↻",
                fill=T.STATUS_BUSY,
                font=(T.FONT_FAMILY, 10, "bold"),
                tags=("node", node.node_id),
            )

        # Edge handle (right side of node) for creating edges
        handle_x = x + _NODE_W
        handle_y = y + _NODE_H / 2
        self._canvas.create_oval(
            handle_x - _EDGE_HANDLE_SIZE / 2,
            handle_y - _EDGE_HANDLE_SIZE / 2,
            handle_x + _EDGE_HANDLE_SIZE / 2,
            handle_y + _EDGE_HANDLE_SIZE / 2,
            fill=T.ACCENT_DEFAULT,
            outline="",
            tags=("edge_handle", "edge_handle_" + node.node_id),
        )

    def _draw_edge(self, edge: GraphEdge) -> None:
        if self._graph is None:
            return
        src = self._graph.node_by_id(edge.source_id)
        tgt = self._graph.node_by_id(edge.target_id)
        if src is None or tgt is None:
            return

        sx = src.x + _NODE_W
        sy = src.y + _NODE_H / 2
        tx = tgt.x
        ty = tgt.y + _NODE_H / 2

        edge_key = (edge.source_id, edge.target_id)
        edge_id = f"{edge.source_id}->{edge.target_id}"
        mid_x = (sx + tx) / 2
        mid_y = (sy + ty) / 2
        self._edge_bounds[edge_key] = (mid_x - 15, mid_y - 8, mid_x + 15, mid_y + 8)

        is_selected = edge_id in self._selected_edge_ids
        line_color = T.ACCENT_DEFAULT if is_selected else T.BG_GLASS_BORDER
        line_width = 3 if is_selected else 2

        self._canvas.create_line(
            sx, sy, tx, ty,
            fill=line_color,
            width=line_width,
            arrow=tk.LAST,
            arrowshape=(8, 10, 4),
            tags=("edge", f"edge_{edge.source_id}_{edge.target_id}"),
        )

    def _hit_test(self, canvas_x: float, canvas_y: float) -> GraphNode | None:
        if self._graph is None:
            return None
        for node in self._graph.nodes:
            x0, y0, x1, y1 = self._node_bounds.get(node.node_id, (0, 0, 0, 0))
            if x0 <= canvas_x <= x1 and y0 <= canvas_y <= y1:
                return node
        return None

    def _hit_test_edge_handle(self, canvas_x: float, canvas_y: float) -> str | None:
        """Check if click is on an edge handle. Returns node_id or None."""
        if self._graph is None:
            return None
        for node in self._graph.nodes:
            hx = node.x + _NODE_W
            hy = node.y + _NODE_H / 2
            dist = ((canvas_x - hx) ** 2 + (canvas_y - hy) ** 2) ** 0.5
            if dist <= _EDGE_HANDLE_SIZE:
                return node.node_id
        return None

    def _hit_test_edge(self, canvas_x: float, canvas_y: float) -> tuple[str, str] | None:
        """Check if click is on an edge. Returns (source_id, target_id) or None."""
        for (src_id, tgt_id), (x0, y0, x1, y1) in self._edge_bounds.items():
            if x0 <= canvas_x <= x1 and y0 <= canvas_y <= y1:
                return (src_id, tgt_id)
        return None

    def _on_canvas_press(self, event: tk.Event) -> None:
        """Handle left mouse button press."""
        if self._graph is None:
            return
        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)

        # Check if clicking on edge handle to start drawing an edge
        handle_node_id = self._hit_test_edge_handle(canvas_x, canvas_y)
        if handle_node_id:
            self._edge_draw_start = (canvas_x, canvas_y)
            self._edge_draw_source_id = handle_node_id
            self._selected_node_ids.clear()
            self._selected_edge_ids.clear()
            return

        # Check if clicking on a node
        node = self._hit_test(canvas_x, canvas_y)
        if node is not None:
            # If we were drawing an edge, complete it
            if self._edge_draw_source_id and self._edge_draw_source_id != node.node_id:
                self._on_edge_create(self._edge_draw_source_id, node.node_id)
                self._edge_draw_start = None
                self._edge_draw_source_id = ""
                return

            # Toggle selection with Ctrl, otherwise select single
            if event.state & 0x4:  # Ctrl modifier
                if node.node_id in self._selected_node_ids:
                    self._selected_node_ids.discard(node.node_id)
                else:
                    self._selected_node_ids.add(node.node_id)
            else:
                self._selected_node_ids = {node.node_id}
                self._selected_edge_ids.clear()

            self._drag_node_id = node.node_id
            self._drag_offset = (canvas_x - node.x, canvas_y - node.y)
            if len(self._selected_node_ids) == 1:
                self._on_node_select(node)
            self.render(self._graph, selected_node_ids=self._selected_node_ids)
            return

        # Check if clicking on an edge
        edge_hit = self._hit_test_edge(canvas_x, canvas_y)
        if edge_hit:
            src_id, tgt_id = edge_hit
            edge_id = f"{src_id}->{tgt_id}"
            if event.state & 0x4:  # Ctrl modifier
                if edge_id in self._selected_edge_ids:
                    self._selected_edge_ids.discard(edge_id)
                else:
                    self._selected_edge_ids.add(edge_id)
            else:
                self._selected_edge_ids = {edge_id}
                self._selected_node_ids.clear()
            if self._graph:
                self.render(self._graph, selected_edge_ids=self._selected_edge_ids)
            return

        # Clear selection on empty canvas click (unless Shift for selection box)
        if not (event.state & 0x1):  # Not Shift
            self._selected_node_ids.clear()
            self._selected_edge_ids.clear()
            if self._graph:
                self.render(self._graph)

    def _on_selection_start(self, event: tk.Event) -> None:
        """Start selection box on Shift+click."""
        if self._graph is None:
            return
        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)
        self._selection_start = (canvas_x, canvas_y)
        self._selection_box = self._canvas.create_rectangle(
            canvas_x, canvas_y, canvas_x, canvas_y,
            outline=T.ACCENT_DEFAULT,
            dash=(4, 4),
            width=1,
        )

    def _on_selection_drag(self, event: tk.Event) -> None:
        """Update selection box as mouse moves."""
        if self._selection_start is None or self._selection_box is None:
            return
        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)
        x0, y0 = self._selection_start
        self._canvas.coords(self._selection_box, x0, y0, canvas_x, canvas_y)

    def _on_canvas_drag(self, event: tk.Event) -> None:
        """Handle mouse drag for node movement."""
        # Don't drag if we have a selection box
        if self._selection_start is not None:
            return
        if not self._drag_node_id or self._graph is None:
            return
        node = self._graph.node_by_id(self._drag_node_id)
        if node is None:
            return
        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)
        node.x = max(0.0, canvas_x - self._drag_offset[0])
        node.y = max(0.0, canvas_y - self._drag_offset[1])
        self.render(self._graph, selected_node_ids=self._selected_node_ids)

    def _on_canvas_release(self, event: tk.Event) -> None:
        """Handle mouse button release."""
        # Handle selection box completion
        if self._selection_start is not None and self._selection_box is not None:
            canvas_x = self._canvas.canvasx(event.x)
            canvas_y = self._canvas.canvasy(event.y)
            x0, y0 = self._selection_start
            # Select all nodes within the box
            self._selected_node_ids.clear()
            self._selected_edge_ids.clear()
            for node in (self._graph.nodes if self._graph else []):
                if (min(x0, canvas_x) <= node.x <= max(x0, canvas_x) and
                    min(y0, canvas_y) <= node.y <= max(y0, canvas_y)):
                    self._selected_node_ids.add(node.node_id)
            self._canvas.delete(self._selection_box)
            self._selection_box = None
            self._selection_start = None
            if self._graph:
                self.render(self._graph, selected_node_ids=self._selected_node_ids)
            return

        # Handle edge drawing
        if self._edge_draw_start is not None:
            self._edge_draw_start = None
            self._edge_draw_source_id = ""
            return

        # Handle node movement
        if not self._drag_node_id or self._graph is None:
            return
        node = self._graph.node_by_id(self._drag_node_id)
        if node is not None:
            # Record the move for undo
            action = EditAction(
                action_type=EditActionType.NODE_MOVE,
                node_id=node.node_id,
                old_x=node.x,
                old_y=node.y,
            )
            self._history.push(action)
            self._on_node_move(node.node_id, node.x, node.y)
        self._drag_node_id = ""

    def _on_pan_start(self, event: tk.Event) -> None:
        """Start panning with middle mouse button."""
        self._pan_mode = True
        self._pan_start = (self._canvas.canvasx(event.x), self._canvas.canvasy(event.y))

    def _on_pan_drag(self, event: tk.Event) -> None:
        """Pan the canvas."""
        if not self._pan_mode or self._pan_start is None:
            return
        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)
        dx = canvas_x - self._pan_start[0]
        dy = canvas_y - self._pan_start[1]
        self._canvas.scan_dragto(event.x, event.y, gain=1)
        self._pan_start = (canvas_x, canvas_y)

    def _on_pan_end(self, event: tk.Event) -> None:
        """End panning."""
        self._pan_mode = False
        self._pan_start = None

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        """Handle mouse wheel for zooming."""
        if self._graph is None:
            return
        delta = event.delta
        if delta > 0:
            self._zoom_level = min(self._zoom_max, self._zoom_level + self._zoom_step)
        elif delta < 0:
            self._zoom_level = max(self._zoom_min, self._zoom_level - self._zoom_step)
        self.render(self._graph, selected_node_ids=self._selected_node_ids)

    def _on_focus_in(self, event: tk.Event) -> None:
        """Handle focus change - ensure canvas maintains keyboard focus."""
        pass  # Canvas focus is set in __init__

    def _on_key_press(self, event: tk.Event) -> None:
        """Handle keyboard shortcuts."""
        if self._graph is None:
            return

        # Ctrl+Z - Undo
        if event.state & 0x4 and event.keysym == "z":  # Ctrl+Z
            self._handle_undo()
        # Ctrl+Y or Ctrl+Shift+Z - Redo
        elif event.state & 0x4 and (event.keysym == "y" or
              (event.keysym == "Z" and event.state & 0x1)):  # Ctrl+Shift+Z
            self._handle_redo()
        # Ctrl+A - Select all
        elif event.state & 0x4 and event.keysym == "a":
            self._selected_node_ids = {n.node_id for n in self._graph.nodes}
            self._selected_edge_ids.clear()
            self.render(self._graph, selected_node_ids=self._selected_node_ids)
        # Delete - Delete selected
        elif event.keysym == "Delete" or event.keysym == "BackSpace":
            self._delete_selected()
        # Escape - Clear selection
        elif event.keysym == "Escape":
            self._selected_node_ids.clear()
            self._selected_edge_ids.clear()
            self.render(self._graph)

    def _handle_undo(self) -> None:
        """Handle undo operation."""
        action = self._history.pop_undo()
        if action is None:
            return
        self._on_undo()
        # Note: actual undo logic is handled by parent

    def _handle_redo(self) -> None:
        """Handle redo operation."""
        action = self._history.pop_redo()
        if action is None:
            return
        self._on_redo()
        # Note: actual redo logic is handled by parent

    def _delete_selected(self) -> None:
        """Delete all selected nodes and edges."""
        if self._graph is None:
            return
        # Delete selected edges first
        for edge_id in list(self._selected_edge_ids):
            parts = edge_id.split("->")
            if len(parts) == 2:
                self._delete_edge(parts[0], parts[1])
        # Delete selected nodes
        for node_id in list(self._selected_node_ids):
            # TODO: Call on_node_delete when implemented
            pass
        self._selected_node_ids.clear()
        self._selected_edge_ids.clear()

    def _on_canvas_context(self, event: tk.Event) -> None:
        """Show context menu on right-click."""
        if self._context_menu:
            self._context_menu.destroy()

        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)

        # Check what's under the cursor
        node = self._hit_test(canvas_x, canvas_y)
        edge_hit = self._hit_test_edge(canvas_x, canvas_y)

        if node is None and edge_hit is None:
            return  # No action for empty space

        self._context_menu = tk.Menu(self._canvas, tearoff=0)
        if node is not None:
            self._context_menu.add_command(
                label=f"Edit '{node.label[:12]}'...",
                command=lambda: self._on_node_select(node),
            )
            self._context_menu.add_separator()
        if edge_hit is not None:
            src_id, tgt_id = edge_hit
            self._context_menu.add_command(
                label="Delete Edge",
                command=lambda: self._delete_edge(src_id, tgt_id),
            )
            if node is None:
                self._context_menu.add_separator()

        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _on_canvas_double_click(self, event: tk.Event) -> None:
        """Handle double-click on edge to select it for deletion."""
        if self._graph is None:
            return
        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)
        edge_hit = self._hit_test_edge(canvas_x, canvas_y)
        if edge_hit is not None:
            src_id, tgt_id = edge_hit
            self._delete_edge(src_id, tgt_id)

    def _delete_edge(self, source_id: str, target_id: str) -> None:
        """Delete the edge between source_id and target_id."""
        if self._graph is None:
            return
        for edge in self._graph.edges:
            if edge.source_id == source_id and edge.target_id == target_id:
                edge_id = f"{source_id}->{target_id}"
                self._selected_edge_ids.discard(edge_id)
                self._on_edge_delete(edge)
                break

    # Public API for zoom controls
    def zoom_in(self) -> None:
        """Zoom in by one step."""
        if self._graph is None:
            return
        self._zoom_level = min(self._zoom_max, self._zoom_level + self._zoom_step)
        self.render(self._graph, selected_node_ids=self._selected_node_ids)

    def zoom_out(self) -> None:
        """Zoom out by one step."""
        if self._graph is None:
            return
        self._zoom_level = max(self._zoom_min, self._zoom_level - self._zoom_step)
        self.render(self._graph, selected_node_ids=self._selected_node_ids)

    def zoom_reset(self) -> None:
        """Reset zoom to 100%."""
        if self._graph is None:
            return
        self._zoom_level = 1.0
        self.render(self._graph, selected_node_ids=self._selected_node_ids)

    def get_zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom_level

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._history.can_undo()

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._history.can_redo()

    def record_node_move(self, node_id: str, old_x: float, old_y: float) -> None:
        """Record a node move for undo."""
        self._history.push(EditAction(
            action_type=EditActionType.NODE_MOVE,
            node_id=node_id,
            old_x=old_x,
            old_y=old_y,
        ))


__all__ = ["GraphCanvas"]
