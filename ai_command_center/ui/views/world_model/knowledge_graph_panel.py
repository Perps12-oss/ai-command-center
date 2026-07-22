"""Knowledge Graph panel — World Model projection onto shared BaseGraphCanvas."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
)
from ai_command_center.ui.components.graph import (
    BaseGraphCanvas,  # noqa: F401 — ADR gate: panels must reuse shared graph package
    GraphEdgeVisual,
    GraphNodeVisual,
    circular_layout,
)
from ai_command_center.ui.components.world_model.world_graph_canvas import WorldGraphCanvas
from ai_command_center.ui.design_system import theme_v2 as T


class KnowledgeGraphPanel(ctk.CTkFrame):
    """Renders world-model nodes/edges via WorldGraphCanvas (BaseGraphCanvas)."""

    _NODE_R = 22.0
    _SURFACE_TYPE = BaseGraphCanvas  # shared primitive identity for architecture gates

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
        on_activate: Callable[[str], None] | None = None,
        canvas_height: int = 240,
        title: str = "Knowledge Graph",
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.WORLD_TEAL,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        self._on_select = on_select
        self._on_activate = on_activate
        self._nodes: tuple[NodeSnapshot, ...] = ()
        self._edges: tuple[EdgeSnapshot, ...] = ()
        self._selected_id = ""
        self._visible_ids: set[str] | None = None
        self._projecting = False

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text=title,
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")

        self._surface = WorldGraphCanvas(
            self,
            on_node_select=self._click,
        )
        self._surface.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._surface.tk_canvas.configure(height=canvas_height)
        # Relayout when the shared surface resizes
        self._surface.tk_canvas.bind("<Configure>", lambda _e: self._project(), add="+")
        self._surface.tk_canvas.bind("<Double-Button-1>", self._double_click, add="+")

    def apply_snapshot(
        self,
        wm: WorldModelSnapshot,
        *,
        visible_nodes: Sequence[NodeSnapshot] | None = None,
    ) -> None:
        self._nodes = wm.nodes
        self._edges = wm.edges
        self._selected_id = wm.selected_node_id
        if visible_nodes is None:
            self._visible_ids = None
        else:
            self._visible_ids = {n.node_id for n in visible_nodes}
        self._project()

    def _project(self) -> None:
        if self._projecting:
            return
        self._projecting = True
        try:
            width = max(int(self._surface.tk_canvas.winfo_width() or 400), 200)
            height = max(int(self._surface.tk_canvas.winfo_height() or 240), 160)
            nodes = list(self._nodes)
            if self._visible_ids is not None:
                nodes = [n for n in nodes if n.node_id in self._visible_ids]
            if not nodes:
                self._surface.set_scene([], [])
                return

            visible_ids = {n.node_id for n in nodes}
            positions = circular_layout(
                [n.node_id for n in nodes],
                width=float(width),
                height=float(height),
                node_radius=self._NODE_R,
            )
            visuals = [
                GraphNodeVisual(
                    node_id=node.node_id,
                    x=positions[node.node_id][0],
                    y=positions[node.node_id][1],
                    label=(node.label or node.node_id)[:10],
                    width=self._NODE_R * 2,
                    height=self._NODE_R * 2,
                    shape="oval",
                    fill=T.HERO_CYAN_DIM if node.node_id == self._selected_id else T.BG_GLASS,
                    outline=T.HERO_CYAN if node.node_id == self._selected_id else T.WORLD_TEAL,
                    outline_width=2 if node.node_id == self._selected_id else 1,
                    text_color=T.TEXT_PRIMARY,
                    font_size=8,
                )
                for node in nodes
            ]
            edges = [
                GraphEdgeVisual(
                    edge_id=GraphEdgeVisual.make_id(e.from_node_id, e.to_node_id),
                    source_id=e.from_node_id,
                    target_id=e.to_node_id,
                    color=T.WORLD_TEAL,
                    width=1,
                    arrow="none",
                )
                for e in self._edges
                if e.from_node_id in visible_ids and e.to_node_id in visible_ids
            ]
            selected = {self._selected_id} if self._selected_id else set()
            self._surface.set_scene(visuals, edges, selected_node_ids=selected)
        finally:
            self._projecting = False

    def _click(self, node_id: str) -> None:
        if self._on_select:
            self._on_select(node_id)

    def _double_click(self, event: Any) -> None:
        if self._on_activate is None:
            return
        canvas_x, canvas_y = self._surface._event_xy(event)
        node = self._surface.hit_test_node(canvas_x, canvas_y)
        if node is not None:
            self._on_activate(node.node_id)


__all__ = ["KnowledgeGraphPanel"]
