"""RelationshipView — visualize edges for a selected World Model node.

Architecture contract:
- Pure display widget. No repository access. No service calls.
- Reads from WorldModelState (AppState layer).
- Publishes WORLD_MODEL_NODE_SELECTED when user navigates to a connected node.
- Graph drawing reuses shared BaseGraphCanvas (no private canvas engine).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import WORLD_MODEL_NODE_SELECTED
from ai_command_center.core.state.world_model_state import EdgeSummary, NodeSummary, WorldModelState
from ai_command_center.ui.components.graph import (
    BaseGraphCanvas,
    GraphEdgeVisual,
    GraphNodeVisual,
    radial_layout,
)
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

_NODE_R = 28.0
_CANVAS_W = 340.0
_CANVAS_H = 260.0


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


class RelationshipView(ctk.CTkFrame):
    """World Model edge visualizer.

    Top: radial graph via shared BaseGraphCanvas.
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

        self._surface = BaseGraphCanvas(
            self,
            on_node_select=self._on_graph_select,
            enable_zoom=False,
            enable_pan=False,
            enable_multi_select=False,
            enable_node_drag=False,
            enable_selection_box=False,
            show_scrollbars=False,
            empty_message="Select a node",
            canvas_bg=T.BG_PANEL,
        )
        self._surface.pack(fill="x", padx=12, pady=(8, 4))
        self._surface.tk_canvas.configure(width=int(_CANVAS_W), height=int(_CANVAS_H))

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

        if node:
            self._node_label.configure(text=f"Node: {node.label}")
        else:
            self._node_label.configure(text="no node selected")

        self._project_graph(node, edges)
        self._render_edge_list(edges, node)

    def _project_graph(
        self,
        center_node: NodeSummary | None,
        edges: list[EdgeSummary],
    ) -> None:
        if center_node is None:
            self._surface.set_scene([], [])
            return

        peers: list[tuple[str, str, str, str]] = []
        for edge in edges:
            if edge.from_node_id == center_node.node_id:
                peers.append(
                    (
                        edge.to_node_id,
                        edge.to_label or edge.to_node_id[:10],
                        "forward",
                        edge.edge_type,
                    )
                )
            else:
                peers.append(
                    (
                        edge.from_node_id,
                        edge.from_label or edge.from_node_id[:10],
                        "backward",
                        edge.edge_type,
                    )
                )

        positions = radial_layout(
            center_node.node_id,
            [p[0] for p in peers],
            width=_CANVAS_W,
            height=_CANVAS_H,
        )

        visuals: list[GraphNodeVisual] = [
            GraphNodeVisual(
                node_id=center_node.node_id,
                x=positions[center_node.node_id][0],
                y=positions[center_node.node_id][1],
                label=center_node.label[:10],
                width=_NODE_R * 2,
                height=_NODE_R * 2,
                shape="oval",
                fill=T.ACCENT_DEFAULT,
                outline=T.HERO_CYAN,
                outline_width=2,
                text_color=T.TEXT_PRIMARY,
                font_size=9,
                font_bold=True,
            )
        ]
        edge_visuals: list[GraphEdgeVisual] = []
        for peer_id, peer_label, arrow, edge_type in peers:
            color = _edge_color(edge_type)
            px, py = positions[peer_id]
            visuals.append(
                GraphNodeVisual(
                    node_id=peer_id,
                    x=px,
                    y=py,
                    label=peer_label[:8],
                    width=_NODE_R * 2,
                    height=_NODE_R * 2,
                    shape="oval",
                    fill=T.BG_GLASS,
                    outline=color,
                    outline_width=2,
                    text_color=T.TEXT_PRIMARY,
                    font_size=9,
                    secondary_label=edge_type[:8],
                    secondary_color=color,
                )
            )
            # Directional edge from center to peer (arrow encodes inbound/outbound)
            if arrow == "forward":
                edge_visuals.append(
                    GraphEdgeVisual(
                        edge_id=GraphEdgeVisual.make_id(center_node.node_id, peer_id),
                        source_id=center_node.node_id,
                        target_id=peer_id,
                        color=color,
                        width=2,
                        arrow="forward",
                    )
                )
            else:
                edge_visuals.append(
                    GraphEdgeVisual(
                        edge_id=GraphEdgeVisual.make_id(peer_id, center_node.node_id),
                        source_id=peer_id,
                        target_id=center_node.node_id,
                        color=color,
                        width=2,
                        arrow="forward",
                    )
                )

        self._surface.set_scene(
            visuals,
            edge_visuals,
            selected_node_ids={center_node.node_id},
        )

    def _on_graph_select(self, node_id: str) -> None:
        center = self._state.selected_node
        if center is not None and node_id == center.node_id:
            return
        self._navigate_to(node_id)

    def _render_edge_list(self, edges: list[EdgeSummary], node: NodeSummary | None) -> None:
        clear_children(self._edge_list)
        if not edges:
            ctk.CTkLabel(
                self._edge_list,
                text=(
                    "No relationships for this node."
                    if node
                    else "Select a node to view relationships."
                ),
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
