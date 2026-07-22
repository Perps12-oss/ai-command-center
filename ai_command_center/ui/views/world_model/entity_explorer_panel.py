"""Entity Explorer panel — search, filter, sort world-model nodes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import NodeSnapshot, WorldModelSnapshot
from ai_command_center.ui.components.world_model.node_filters import (
    NodeFilterState,
    filter_nodes,
    node_status,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


class EntityExplorerPanel(ctk.CTkFrame):
    """Browse entities with shared NodeFilterState (workspace bar owns controls)."""

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
        self._selected_id = ""
        self._filter = NodeFilterState()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Entity Explorer",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")
        self._count = ctk.CTkLabel(
            header,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._count.pack(side="right")

        self._list = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_DEEP,
            border_width=0,
            corner_radius=T.SMALL_RADIUS,
        )
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(
        self,
        wm: WorldModelSnapshot,
        *,
        filter_state: NodeFilterState | None = None,
    ) -> None:
        self._nodes = wm.nodes
        self._selected_id = wm.selected_node_id
        if filter_state is not None:
            self._filter = filter_state
        self._render()

    def apply_filters(self, filter_state: NodeFilterState) -> None:
        self._filter = filter_state
        self._render()

    def _filtered(self) -> list[NodeSnapshot]:
        return filter_nodes(self._nodes, self._filter)

    def _render(self) -> None:
        clear_children(self._list)
        nodes = self._filtered()
        self._count.configure(text=f"{len(nodes)} shown")
        if not nodes:
            ctk.CTkLabel(
                self._list,
                text=(
                    "No entities match the current filters.\n"
                    "Entities appear when the World Model is indexed or New Entity is used.\n"
                    "Next: clear filters or create an entity from the hero action."
                ),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                justify="left",
            ).pack(pady=24)
            return
        for node in nodes:
            selected = node.node_id == self._selected_id
            row = ctk.CTkFrame(
                self._list,
                fg_color=T.BG_INPUT if selected else T.BG_GLASS,
                border_color=T.WORLD_TEAL if selected else T.BG_GLASS_BORDER,
                border_width=1,
                corner_radius=T.SMALL_RADIUS,
            )
            row.pack(fill="x", pady=2)
            nid = node.node_id
            row.bind("<Button-1>", lambda _e, i=nid: self._click(i))

            name = ctk.CTkLabel(
                row,
                text=node.label or node.node_id,
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            )
            name.pack(side="left", padx=(8, 4), pady=6)
            name.bind("<Button-1>", lambda _e, i=nid: self._click(i))

            typ = ctk.CTkLabel(
                row,
                text=node.node_type or "—",
                font=T.FONT_SMALL,
                text_color=T.WORLD_TEAL,
                anchor="w",
            )
            typ.pack(side="left", padx=4)
            typ.bind("<Button-1>", lambda _e, i=nid: self._click(i))

            status = ctk.CTkLabel(
                row,
                text=node_status(node),
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
                anchor="e",
            )
            status.pack(side="right", padx=8)
            status.bind("<Button-1>", lambda _e, i=nid: self._click(i))

    def _click(self, node_id: str) -> None:
        if self._on_select:
            self._on_select(node_id)
