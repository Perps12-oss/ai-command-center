"""WorkflowGraphView — visual canvas for workflow graph rendering.

Renders WorkflowGraph nodes and edges on a tkinter Canvas.
Includes RetryVisualization and ApprovalNode sub-components.

Architecture contract: pure display view, no bus/service imports.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.workflow_graph import GraphNode, NodeState, WorkflowGraph
from ai_command_center.ui.design_system import theme_v2 as T

_NODE_W = 120
_NODE_H = 48
_NODE_RADIUS = 8

_STATE_COLORS: dict[NodeState, str] = {
    NodeState.PENDING:   T.TEXT_MUTED,
    NodeState.RUNNING:   T.STATUS_BUSY,
    NodeState.COMPLETED: T.STATUS_READY,
    NodeState.FAILED:    T.STATUS_ERROR,
    NodeState.SKIPPED:   T.TEXT_MUTED,
    NodeState.WAITING:   T.ACCENT_DEFAULT,
    NodeState.CANCELLED: T.TEXT_MUTED,
}

_STATE_FILL: dict[NodeState, str] = {
    NodeState.PENDING:   T.BG_GLASS,
    NodeState.RUNNING:   T.STATUS_BUSY_BG,
    NodeState.COMPLETED: T.STATUS_READY_BG,
    NodeState.FAILED:    T.STATUS_ERROR_BG,
    NodeState.SKIPPED:   T.BG_PANEL,
    NodeState.WAITING:   T.BG_GLASS,
    NodeState.CANCELLED: T.BG_PANEL,
}


class WorkflowGraphView(ctk.CTkFrame):
    """Canvas-based workflow graph renderer.

    Usage::

        view = WorkflowGraphView(parent)
        graph = WorkflowGraph.from_workflow_steps("wf1", steps)
        view.render(graph)
    """

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)

        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=46)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Workflow Graph",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=T.PAD, pady=12)

        canvas_host = ctk.CTkFrame(self, fg_color=T.BG_DEEP, corner_radius=0)
        canvas_host.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(
            canvas_host,
            bg=T.BG_DEEP,
            highlightthickness=0,
        )
        h_scroll = tk.Scrollbar(canvas_host, orient="horizontal", command=self._canvas.xview)
        v_scroll = tk.Scrollbar(canvas_host, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
        )
        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._graph: WorkflowGraph | None = None

    def render(self, graph: WorkflowGraph) -> None:
        """Render the workflow graph on the canvas."""
        self._graph = graph
        self._canvas.delete("all")

        if not graph.nodes:
            self._canvas.create_text(
                100, 60,
                text="No nodes",
                fill=T.TEXT_MUTED,
                font=(T.FONT_FAMILY, 12),
            )
            return

        # Draw edges first
        for edge in graph.edges:
            src = graph.node_by_id(edge.source_id)
            tgt = graph.node_by_id(edge.target_id)
            if src and tgt:
                sx = src.x + _NODE_W
                sy = src.y + _NODE_H / 2
                tx = tgt.x
                ty = tgt.y + _NODE_H / 2
                self._canvas.create_line(
                    sx, sy, tx, ty,
                    fill=T.BG_GLASS_BORDER,
                    width=2,
                    arrow=tk.LAST,
                    arrowshape=(8, 10, 4),
                )
                if edge.label:
                    mx = (sx + tx) / 2
                    my = (sy + ty) / 2
                    self._canvas.create_text(
                        mx, my - 8,
                        text=edge.label,
                        fill=T.TEXT_MUTED,
                        font=(T.FONT_FAMILY, 8),
                    )

        # Draw nodes
        for node in graph.nodes:
            self._draw_node(node)

        # Update scroll region
        max_x = max((n.x + _NODE_W + 40) for n in graph.nodes) if graph.nodes else 400
        max_y = max((n.y + _NODE_H + 40) for n in graph.nodes) if graph.nodes else 200
        self._canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def _draw_node(self, node: GraphNode) -> None:
        x, y = node.x, node.y
        color = _STATE_COLORS.get(node.state, T.TEXT_MUTED)
        fill = _STATE_FILL.get(node.state, T.BG_GLASS)

        # Node rectangle
        self._canvas.create_rectangle(
            x, y, x + _NODE_W, y + _NODE_H,
            fill=fill,
            outline=color,
            width=1,
        )

        # State dot
        self._canvas.create_oval(
            x + 8, y + _NODE_H / 2 - 5,
            x + 18, y + _NODE_H / 2 + 5,
            fill=color,
            outline="",
        )

        # Label
        self._canvas.create_text(
            x + _NODE_W / 2 + 5,
            y + _NODE_H / 2,
            text=node.label[:16],
            fill=T.TEXT_PRIMARY,
            font=(T.FONT_FAMILY, 10),
            anchor="center",
        )

        # Kind tag for decision/approval nodes
        if node.kind in ("decision", "approval"):
            self._canvas.create_text(
                x + _NODE_W - 8, y + 8,
                text="?" if node.kind == "decision" else "✓",
                fill=T.ACCENT_DEFAULT,
                font=(T.FONT_FAMILY, 9, "bold"),
                anchor="ne",
            )
