"""Knowledge Graph panel — visual nodes/edges with WORLD_TEAL accent."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
)
from ai_command_center.ui.design_system import theme_v2 as T


class KnowledgeGraphPanel(ctk.CTkFrame):
    """Renders world-model nodes and relationships; click publishes selection."""

    _NODE_R = 22

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

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Knowledge Graph",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")

        self._canvas = tk.Canvas(
            self,
            bg=T.BG_DEEP,
            highlightthickness=0,
            height=240,
        )
        self._canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._canvas.bind("<Configure>", lambda _e: self._redraw())

    def apply_snapshot(self, wm: WorldModelSnapshot) -> None:
        self._nodes = wm.nodes
        self._edges = wm.edges
        self._selected_id = wm.selected_node_id
        self._redraw()

    def _redraw(self) -> None:
        self._canvas.delete("all")
        width = max(int(self._canvas.winfo_width() or 400), 200)
        height = max(int(self._canvas.winfo_height() or 240), 160)
        nodes = self._nodes
        if not nodes:
            self._canvas.create_text(
                width // 2,
                height // 2,
                text=(
                    "No entities in the World Model yet.\n"
                    "Entities appear when notes, goals, or workspace activity is indexed.\n"
                    "Next: click New Entity or open Goals/Chat to create linked work."
                ),
                fill=T.TEXT_MUTED,
                font=(T.FONT_FAMILY, 11),
                justify="center",
                width=max(width - 40, 120),
            )
            return

        positions = self._layout(nodes, width, height)
        for edge in self._edges:
            a = positions.get(edge.from_node_id)
            b = positions.get(edge.to_node_id)
            if a is None or b is None:
                continue
            self._canvas.create_line(
                a[0], a[1], b[0], b[1],
                fill=T.WORLD_TEAL,
                width=1,
            )

        r = self._NODE_R
        for node in nodes:
            x, y = positions[node.node_id]
            selected = node.node_id == self._selected_id
            outline = T.HERO_CYAN if selected else T.WORLD_TEAL
            fill = T.HERO_CYAN_DIM if selected else T.BG_GLASS
            tag = f"node_{node.node_id}"
            self._canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill=fill,
                outline=outline,
                width=2 if selected else 1,
                tags=(tag,),
            )
            self._canvas.create_text(
                x, y,
                text=(node.label or node.node_id)[:10],
                fill=T.TEXT_PRIMARY,
                font=(T.FONT_FAMILY, 8),
                tags=(tag,),
            )
            nid = node.node_id
            self._canvas.tag_bind(tag, "<Button-1>", lambda _e, i=nid: self._click(i))

    def _layout(
        self,
        nodes: tuple[NodeSnapshot, ...],
        width: int,
        height: int,
    ) -> dict[str, tuple[int, int]]:
        cx, cy = width // 2, height // 2
        n = len(nodes)
        if n == 1:
            return {nodes[0].node_id: (cx, cy)}
        radius = min(width, height) // 2 - self._NODE_R - 12
        radius = max(radius, 40)
        positions: dict[str, tuple[int, int]] = {}
        for i, node in enumerate(nodes):
            angle = (2 * math.pi * i / n) - (math.pi / 2)
            positions[node.node_id] = (
                cx + int(radius * math.cos(angle)),
                cy + int(radius * math.sin(angle)),
            )
        return positions

    def _click(self, node_id: str) -> None:
        if self._on_select:
            self._on_select(node_id)
