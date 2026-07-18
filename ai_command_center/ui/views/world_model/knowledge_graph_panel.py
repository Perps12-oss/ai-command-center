"""Knowledge Graph panel — World Model projection onto shared BaseGraphCanvas."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
)
from ai_command_center.ui.components.graph import (
    BaseGraphCanvas,
    GraphEdgeVisual,
    GraphNodeVisual,
    circular_layout,
)
from ai_command_center.ui.design_system import theme_v2 as T


class KnowledgeGraphPanel(ctk.CTkFrame):
    """Renders world-model nodes/edges via the shared graph primitive."""

    _NODE_R = 22.0

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.WORLD_TEAL,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
        )
        self._on_select = on_select
        self._nodes: tuple[NodeSnapshot, ...] = ()
        self._edges: tuple[EdgeSnapshot, ...] = ()
        self._selected_id = ""
        self._projecting = False

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Knowledge Graph",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")

        self._surface = BaseGraphCanvas(
            self,
            on_node_select=self._click,
            enable_zoom=True,
            enable_pan=True,
            enable_multi_select=False,
            enable_node_drag=False,
            enable_selection_box=False,
            show_scrollbars=False,
            empty_message="No entities in World Model",
            canvas_bg=T.BG_DEEP,
        )
        self._surface.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._surface.tk_canvas.configure(height=240)
        # Relayout when the shared surface resizes
        self._surface.tk_canvas.bind("<Configure>", lambda _e: self._project(), add="+")

    def apply_snapshot(self, wm: WorldModelSnapshot) -> None:
        self._nodes = wm.nodes
        self._edges = wm.edges
        self._selected_id = wm.selected_node_id
        self._project()

    def _project(self) -> None:
        if self._projecting:
            return
        self._projecting = True
        try:
            width = max(int(self._surface.tk_canvas.winfo_width() or 400), 200)
            height = max(int(self._surface.tk_canvas.winfo_height() or 240), 160)
            if not self._nodes:
                self._surface.set_scene([], [])
                return

            positions = circular_layout(
                [n.node_id for n in self._nodes],
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
                for node in self._nodes
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
            ]
            selected = {self._selected_id} if self._selected_id else set()
            self._surface.set_scene(visuals, edges, selected_node_ids=selected)
        finally:
            self._projecting = False

    def _click(self, node_id: str) -> None:
        if self._on_select:
            self._on_select(node_id)


__all__ = ["KnowledgeGraphPanel"]
