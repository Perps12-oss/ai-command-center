"""RelationshipView — visualize edges for a selected World Model node.

Architecture contract:
- Pure display widget. No repository access. No service calls.
- Reads from WorldModelState (AppState layer).
- Publishes WORLD_MODEL_NODE_SELECTED when user navigates to a connected node.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import WORLD_MODEL_NODE_SELECTED
from ai_command_center.core.state.world_model_state import EdgeSummary, NodeSummary, WorldModelState
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children

_DIR_OUTBOUND = "outbound"
_DIR_INBOUND = "inbound"

_EDGE_COLOR = {
    "depends_on": "#EAB308",
    "related": "#3B82F6",
    "contains": "#22C55E",
    "blocks": "#EF4444",
    "requires": "#A78BFA",
    "produces": "#00FFFF",
}


def _edge_color(edge_type: str) -> str:
    return _EDGE_COLOR.get(edge_type, T.TEXT_MUTED)


class _EdgeRow(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        edge: EdgeSummary,
        current_node_id: str,
        on_navigate: Callable[[str], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        direction = _DIR_OUTBOUND if edge.from_node_id == current_node_id else _DIR_INBOUND
        peer_id = edge.to_node_id if direction == _DIR_OUTBOUND else edge.from_node_id
        peer_label = edge.to_label if direction == _DIR_OUTBOUND else edge.from_label
        peer_label = peer_label or peer_id

        dir_arrow = "→" if direction == _DIR_OUTBOUND else "←"
        dir_color = T.ACCENT_DEFAULT if direction == _DIR_OUTBOUND else T.STATUS_BUSY

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=6)

        ctk.CTkLabel(
            left,
            text=dir_arrow,
            font=(T.FONT_FAMILY, 16, "bold"),
            text_color=dir_color,
            width=20,
        ).pack(side="left")

        center = ctk.CTkFrame(left, fg_color="transparent")
        center.pack(side="left", fill="both", expand=True, padx=4)

        type_lbl = ctk.CTkLabel(
            center,
            text=edge.edge_type.upper().replace("_", " "),
            font=(T.FONT_FAMILY, 9, "bold"),
            text_color=_edge_color(edge.edge_type),
            anchor="w",
        )
        type_lbl.pack(fill="x")

        peer_lbl = ctk.CTkLabel(
            center,
            text=peer_label,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        peer_lbl.pack(fill="x")

        id_lbl = ctk.CTkLabel(
            center,
            text=peer_id[:36],
            font=T.FONT_MONO,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        id_lbl.pack(fill="x")

        ctk.CTkButton(
            self,
            text="Go",
            width=40,
            height=24,
            fg_color=T.BG_GLASS_BORDER,
            hover_color=T.ACCENT_DEFAULT,
            text_color=T.TEXT_SECONDARY,
            font=T.FONT_SMALL,
            command=lambda: on_navigate(peer_id),
        ).pack(side="right", padx=(0, 8))


class _GraphCanvas(tk.Canvas):
    """Minimal canvas that draws a radial edge graph for the selected node."""

    _NODE_R = 28
    _CANVAS_W = 340
    _CANVAS_H = 260

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            width=self._CANVAS_W,
            height=self._CANVAS_H,
            bg=T.BG_PANEL,
            highlightthickness=0,
        )
        self._on_peer_click: Callable[[str], None] | None = None
        self._peer_ids: list[str] = []

    def set_click_handler(self, fn: Callable[[str], None]) -> None:
        self._on_peer_click = fn

    def render(
        self,
        center_node: NodeSummary | None,
        edges: list[EdgeSummary],
        all_nodes: dict[str, NodeSummary],
    ) -> None:
        import math

        self.delete("all")
        if center_node is None:
            self.create_text(
                self._CANVAS_W // 2, self._CANVAS_H // 2,
                text="Select a node", fill=T.TEXT_MUTED, font=(T.FONT_FAMILY, 11),
            )
            return

        cx, cy = self._CANVAS_W // 2, self._CANVAS_H // 2
        peers: list[tuple[str, str, str, str]] = []
        for edge in edges:
            if edge.from_node_id == center_node.node_id:
                peer_id = edge.to_node_id
                peer_label = edge.to_label or peer_id[:10]
                arrow = "→"
            else:
                peer_id = edge.from_node_id
                peer_label = edge.from_label or peer_id[:10]
                arrow = "←"
            peers.append((peer_id, peer_label, arrow, edge.edge_type))

        n = len(peers)
        radius = min(100, max(60, 30 * n))

        for i, (peer_id, peer_label, arrow, edge_type) in enumerate(peers):
            angle = (2 * math.pi * i / n) if n > 0 else 0
            px = cx + int(radius * math.cos(angle))
            py = cy + int(radius * math.sin(angle))

            color = _edge_color(edge_type)
            self.create_line(cx, cy, px, py, fill=color, width=2, arrow=tk.LAST if arrow == "→" else tk.FIRST)

            self.create_oval(
                px - self._NODE_R, py - self._NODE_R,
                px + self._NODE_R, py + self._NODE_R,
                fill=T.BG_GLASS, outline=color, width=2,
            )
            self.create_text(px, py - 6, text=peer_label[:8], fill=T.TEXT_PRIMARY, font=(T.FONT_FAMILY, 9))
            self.create_text(px, py + 6, text=edge_type[:8], fill=color, font=(T.FONT_FAMILY, 8))

            tag = f"peer_{i}"
            self.create_oval(
                px - self._NODE_R, py - self._NODE_R,
                px + self._NODE_R, py + self._NODE_R,
                fill="", outline="", tags=tag,
            )
            captured_id = peer_id
            self.tag_bind(tag, "<Button-1>", lambda _e, pid=captured_id: self._click_peer(pid))

        self.create_oval(
            cx - self._NODE_R, cy - self._NODE_R,
            cx + self._NODE_R, cy + self._NODE_R,
            fill=T.ACCENT_DEFAULT, outline=T.HERO_CYAN, width=2,
        )
        label = center_node.label[:10] if center_node else ""
        self.create_text(cx, cy, text=label, fill=T.TEXT_PRIMARY, font=(T.FONT_FAMILY, 9, "bold"))

    def _click_peer(self, peer_id: str) -> None:
        if self._on_peer_click:
            self._on_peer_click(peer_id)


class RelationshipView(ctk.CTkFrame):
    """World Model edge visualizer.

    Top: radial graph canvas.
    Bottom: scrollable edge list with direction, type, and navigate button.
    """

    def __init__(self, master: Any, bus: EventBus, state: WorldModelState) -> None:
        super().__init__(master, fg_color=T.BG_DEEP)
        self._bus = bus
        self._state = state
        self._unsub: Callable[[], None] | None = None
        self._build()
        self._unsub = state.add_listener(self._on_state_change)
        self._refresh()

    def destroy(self) -> None:
        if self._unsub is not None:
            self._unsub()
        super().destroy()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, height=48, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="⟷  Relationships",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(side="left", padx=16, pady=10)

        self._node_label = ctk.CTkLabel(
            header,
            text="no node selected",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._node_label.pack(side="right", padx=16)

        self._canvas = _GraphCanvas(self)
        self._canvas.set_click_handler(self._navigate_to)
        self._canvas.pack(fill="x", padx=12, pady=(8, 4))

        sep = ctk.CTkFrame(self, fg_color=T.BG_GLASS_BORDER, height=1)
        sep.pack(fill="x", padx=12, pady=(0, 4))

        self._edge_list = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_PANEL,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CORNER_RADIUS,
            label_text="",
        )
        self._edge_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _on_state_change(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        node = self._state.selected_node
        edges = self._state.edges_for_selected
        all_nodes = {n.node_id: n for n in self._state.nodes}

        if node:
            self._node_label.configure(text=f"Node: {node.label}")
        else:
            self._node_label.configure(text="no node selected")

        self._canvas.render(node, edges, all_nodes)
        self._render_edge_list(edges, node)

    def _render_edge_list(self, edges: list[EdgeSummary], node: NodeSummary | None) -> None:
        clear_children(self._edge_list)
        if not edges:
            ctk.CTkLabel(
                self._edge_list,
                text="No relationships for this node." if node else "Select a node to view relationships.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                justify="center",
            ).pack(expand=True, pady=20)
            return
        current_id = node.node_id if node else ""
        for edge in edges:
            _EdgeRow(
                self._edge_list,
                edge=edge,
                current_node_id=current_id,
                on_navigate=self._navigate_to,
            ).pack(fill="x", pady=2, padx=2)

    def _navigate_to(self, node_id: str) -> None:
        self._bus.publish(
            WORLD_MODEL_NODE_SELECTED,
            {"node_id": node_id},
            source="relationship_view",
        )
