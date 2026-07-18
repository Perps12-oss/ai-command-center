"""Relationship Explorer — incoming/outgoing edges for the selected node."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import WorldModelSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class RelationshipExplorerPanel(ctk.CTkFrame):
    """Shows connected relationships synchronized with graph selection."""

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

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Relationship Explorer",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")

        self._body = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_DEEP,
            border_width=0,
            corner_radius=T.SMALL_RADIUS,
        )
        self._body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._render_empty()

    def apply_snapshot(self, wm: WorldModelSnapshot) -> None:
        clear_children(self._body)
        node = wm.selected_node
        if node is None:
            self._render_empty()
            return

        incoming = [e for e in wm.edges_for_selected if e.to_node_id == node.node_id]
        outgoing = [e for e in wm.edges_for_selected if e.from_node_id == node.node_id]

        self._section("Incoming")
        if not incoming:
            self._muted("No incoming relationships.")
        for edge in incoming:
            self._edge_row(
                peer_id=edge.from_node_id,
                peer_label=edge.from_label or edge.from_node_id,
                edge_type=edge.edge_type,
                direction="←",
            )

        self._section("Outgoing")
        if not outgoing:
            self._muted("No outgoing relationships.")
        for edge in outgoing:
            self._edge_row(
                peer_id=edge.to_node_id,
                peer_label=edge.to_label or edge.to_node_id,
                edge_type=edge.edge_type,
                direction="→",
            )

    def _render_empty(self) -> None:
        clear_children(self._body)
        self._muted("Select a node to view relationships.")

    def _section(self, title: str) -> None:
        ctk.CTkLabel(
            self._body,
            text=title,
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(8, 2))

    def _muted(self, text: str) -> None:
        ctk.CTkLabel(
            self._body,
            text=text,
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=4, pady=2)

    def _edge_row(
        self,
        *,
        peer_id: str,
        peer_label: str,
        edge_type: str,
        direction: str,
    ) -> None:
        row = ctk.CTkFrame(
            self._body,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
        )
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(
            row,
            text=f"{direction} {peer_label}",
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=8, pady=4)
        ctk.CTkLabel(
            row,
            text=edge_type or "related",
            font=T.FONT_SMALL,
            text_color=T.WORLD_TEAL,
            anchor="e",
        ).pack(side="right", padx=8)
        if self._on_select:
            row.bind("<Button-1>", lambda _e, i=peer_id: self._on_select(i))
