"""Entity Explorer panel — search, filter, sort world-model nodes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.world_model_snapshot import NodeSnapshot, WorldModelSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children


def _node_status(node: NodeSnapshot) -> str:
    for key, value in node.attributes:
        if key.lower() == "status":
            return value
    return "active"


class EntityExplorerPanel(ctk.CTkFrame):
    """Browse entities with search, type/status filters, and sort."""

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
        self._search = ""
        self._type_filter = "all"
        self._status_filter = "all"
        self._sort_key = "name"

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text="Entity Explorer",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", padx=T.PAD, pady=(0, 6))

        self._search_entry = ctk.CTkEntry(
            filters,
            placeholder_text="Search…",
            font=T.FONT_SMALL,
            height=28,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._search_entry.bind("<KeyRelease>", lambda _e: self._on_filters_changed())

        self._type_menu = ctk.CTkOptionMenu(
            filters,
            values=["all", "workspace", "card", "resource", "note", "goal", "task", "file", "service"],
            width=100,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.WORLD_TEAL,
            command=lambda _v: self._on_filters_changed(),
        )
        self._type_menu.set("all")
        self._type_menu.pack(side="left", padx=(0, 6))

        self._status_menu = ctk.CTkOptionMenu(
            filters,
            values=["all", "active", "paused", "complete", "failed", "cancelled"],
            width=100,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.WORLD_TEAL,
            command=lambda _v: self._on_filters_changed(),
        )
        self._status_menu.set("all")
        self._status_menu.pack(side="left", padx=(0, 6))

        self._sort_menu = ctk.CTkOptionMenu(
            filters,
            values=["name", "type", "status"],
            width=90,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            button_color=T.WORLD_TEAL,
            command=lambda _v: self._on_filters_changed(),
        )
        self._sort_menu.set("name")
        self._sort_menu.pack(side="left")

        self._list = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_DEEP,
            border_width=0,
            corner_radius=T.SMALL_RADIUS,
        )
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def apply_snapshot(self, wm: WorldModelSnapshot) -> None:
        self._nodes = wm.nodes
        self._selected_id = wm.selected_node_id
        self._render()

    def _on_filters_changed(self) -> None:
        self._search = str(self._search_entry.get() or "").lower()
        self._type_filter = str(self._type_menu.get() or "all")
        self._status_filter = str(self._status_menu.get() or "all")
        self._sort_key = str(self._sort_menu.get() or "name")
        self._render()

    def _filtered(self) -> list[NodeSnapshot]:
        nodes = list(self._nodes)
        if self._type_filter != "all":
            nodes = [n for n in nodes if n.node_type == self._type_filter]
        if self._status_filter != "all":
            nodes = [n for n in nodes if _node_status(n) == self._status_filter]
        if self._search:
            nodes = [
                n for n in nodes
                if self._search in n.label.lower()
                or self._search in n.node_id.lower()
                or self._search in n.node_type.lower()
            ]
        key = self._sort_key
        if key == "type":
            nodes.sort(key=lambda n: (n.node_type, n.label.lower()))
        elif key == "status":
            nodes.sort(key=lambda n: (_node_status(n), n.label.lower()))
        else:
            nodes.sort(key=lambda n: n.label.lower())
        return nodes

    def _render(self) -> None:
        clear_children(self._list)
        nodes = self._filtered()
        if not nodes:
            ctk.CTkLabel(
                self._list,
                text="No entities match filters.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
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
                text=_node_status(node),
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
                anchor="e",
            )
            status.pack(side="right", padx=8)
            status.bind("<Button-1>", lambda _e, i=nid: self._click(i))

    def _click(self, node_id: str) -> None:
        if self._on_select:
            self._on_select(node_id)
