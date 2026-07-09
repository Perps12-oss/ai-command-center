"""GraphCanvas — tkinter canvas renderer for workflow graphs."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.workflow_graph import GraphNode, NodeState, WorkflowGraph
from ai_command_center.ui.components.workflow_node_overlays import node_overlay_kind
from ai_command_center.ui.design_system import theme_v2 as T

_NODE_W = 120
_NODE_H = 48

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


class GraphCanvas(ctk.CTkFrame):
    """Canvas-based workflow graph renderer with node hit-testing."""

    def __init__(
        self,
        master: Any,
        *,
        on_node_select: Callable[[GraphNode], None] | None = None,
        on_node_move: Callable[[str, float, float], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, corner_radius=0, **kwargs)
        self._on_node_select = on_node_select or (lambda _node: None)
        self._on_node_move = on_node_move or (lambda _node_id, _x, _y: None)
        self._graph: WorkflowGraph | None = None
        self._selected_node_id = ""
        self._node_bounds: dict[str, tuple[float, float, float, float]] = {}
        self._drag_node_id = ""
        self._drag_offset: tuple[float, float] = (0.0, 0.0)

        self._canvas = tk.Canvas(self, bg=T.BG_DEEP, highlightthickness=0)
        h_scroll = tk.Scrollbar(self, orient="horizontal", command=self._canvas.xview)
        v_scroll = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._canvas.bind("<Button-1>", self._on_canvas_press)
        self._canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

    def render(
        self,
        graph: WorkflowGraph,
        *,
        selected_node_id: str = "",
    ) -> None:
        self._graph = graph
        self._selected_node_id = selected_node_id
        self._node_bounds.clear()
        self._canvas.delete("all")

        if not graph.nodes:
            self._canvas.create_text(
                100,
                60,
                text="No nodes",
                fill=T.TEXT_MUTED,
                font=(T.FONT_FAMILY, 12),
            )
            return

        for edge in graph.edges:
            src = graph.node_by_id(edge.source_id)
            tgt = graph.node_by_id(edge.target_id)
            if src and tgt:
                sx = src.x + _NODE_W
                sy = src.y + _NODE_H / 2
                tx = tgt.x
                ty = tgt.y + _NODE_H / 2
                self._canvas.create_line(
                    sx,
                    sy,
                    tx,
                    ty,
                    fill=T.BG_GLASS_BORDER,
                    width=2,
                    arrow=tk.LAST,
                    arrowshape=(8, 10, 4),
                )

        for node in graph.nodes:
            self._draw_node(node)

        max_x = max((n.x + _NODE_W + 40) for n in graph.nodes)
        max_y = max((n.y + _NODE_H + 40) for n in graph.nodes)
        self._canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def _draw_node(self, node: GraphNode) -> None:
        x, y = node.x, node.y
        color = _STATE_COLORS.get(node.state, T.TEXT_MUTED)
        fill = _STATE_FILL.get(node.state, T.BG_GLASS)
        selected = node.node_id == self._selected_node_id
        outline = T.ACCENT_DEFAULT if selected else color
        width = 2 if selected else 1

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

    def _hit_test(self, canvas_x: float, canvas_y: float) -> GraphNode | None:
        if self._graph is None:
            return None
        for node in self._graph.nodes:
            x0, y0, x1, y1 = self._node_bounds.get(node.node_id, (0, 0, 0, 0))
            if x0 <= canvas_x <= x1 and y0 <= canvas_y <= y1:
                return node
        return None

    def _on_canvas_press(self, event: tk.Event) -> None:
        if self._graph is None:
            return
        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)
        node = self._hit_test(canvas_x, canvas_y)
        if node is None:
            return
        self._drag_node_id = node.node_id
        self._selected_node_id = node.node_id
        self._drag_offset = (canvas_x - node.x, canvas_y - node.y)
        self._on_node_select(node)

    def _on_canvas_drag(self, event: tk.Event) -> None:
        if not self._drag_node_id or self._graph is None:
            return
        node = self._graph.node_by_id(self._drag_node_id)
        if node is None:
            return
        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)
        node.x = max(0.0, canvas_x - self._drag_offset[0])
        node.y = max(0.0, canvas_y - self._drag_offset[1])
        self.render(self._graph, selected_node_id=self._selected_node_id)

    def _on_canvas_release(self, event: tk.Event) -> None:
        if not self._drag_node_id or self._graph is None:
            return
        node = self._graph.node_by_id(self._drag_node_id)
        if node is not None:
            self._on_node_move(node.node_id, node.x, node.y)
        self._drag_node_id = ""

    def _on_canvas_click(self, _event: tk.Event) -> None:
        return


__all__ = ["GraphCanvas"]
