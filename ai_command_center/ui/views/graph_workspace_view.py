"""Relationship Graph Workspace — full world-model graph (PR-UI-E12).

Architecture contract:
- Pure renderer. Reads AppState.world_model via apply_state only.
- Reuses KnowledgeGraphPanel / WorldGraphCanvas / NodeFiltersBar / SelectionInspectorPanel.
- No mutable WorldModelState listeners. No second graph engine.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.domain.world_model_snapshot import WorldModelSnapshot
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.components.world_model.graph_renderer import (
    filtered_graph,
    graph_metrics,
)
from ai_command_center.ui.components.world_model.node_filters import (
    NodeFilterState,
    NodeFiltersBar,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    domain_error_from_snap,
    set_surface_state,
)
from ai_command_center.ui.views.world_model import (
    KnowledgeGraphPanel,
    RelationshipExplorerPanel,
    SelectionInspectorPanel,
)


class GraphWorkspaceView(ctk.CTkFrame):
    """Full-graph workspace with filters, inspector, and double-click navigate."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
        on_filter_change: Callable[[NodeFilterState], None] | None = None,
        on_activate: Callable[[str], None] | None = None,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_select = on_select
        self._on_filter_change = on_filter_change
        self._on_activate = on_activate
        self._on_inspect_select = on_inspect_select
        self._on_navigate = on_navigate
        self._filter = NodeFilterState()
        self._last_wm: WorldModelSnapshot | None = None
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.WORLD_TEAL)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            top,
            text="Relationship Graph",
            font=T.FONT_TITLE,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")
        self._metrics = ctk.CTkLabel(
            top,
            text="0/0 nodes · 0 edges",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._metrics.pack(side="right")

        self._hint = ctk.CTkLabel(
            self._hero,
            text="Double-click a node to open World Explorer.",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._hint.pack(fill="x", padx=T.PAD, pady=(8, 4))

        if self._on_navigate is not None:
            ctk.CTkButton(
                self._hero,
                text="Open World Explorer",
                width=160,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.WORLD_TEAL,
                command=lambda: self._on_navigate("world_explorer"),
            ).pack(anchor="e", padx=T.PAD, pady=(0, 8))

        self._surface_state = ctk.CTkLabel(
            self._hero,
            text="Loading…",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self._surface_state.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        self._filters = NodeFiltersBar(self, on_change=self._on_filters)
        self._filters.pack(fill="x", padx=T.PAD, pady=(0, 8))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._graph = KnowledgeGraphPanel(
            body,
            on_select=self._select,
            on_activate=self._activate,
            canvas_height=360,
            title="Full Graph",
        )
        self._graph.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._inspector = SelectionInspectorPanel(right)
        self._inspector.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self._relationships = RelationshipExplorerPanel(right, on_select=self._select)
        self._relationships.grid(row=1, column=0, sticky="nsew")

    def apply_state(self, snapshot: AppState | WorldModelSnapshot | None) -> None:
        if snapshot is None:
            set_surface_state(
                self._surface_state,
                kind="loading",
                message=article18_loading(
                    status="Status: loading Relationship Graph",
                    what="world_model nodes and edges",
                    next_action="Wait for AppState refresh; then filter or select a node.",
                ),
            )
            return
        if isinstance(snapshot, WorldModelSnapshot):
            wm = snapshot
            err = ""
        elif isinstance(snapshot, AppState):
            wm = snapshot.world_model
            err = domain_error_from_snap(
                snapshot, topic_prefixes=("world_model.", "world.")
            )
        else:
            return
        self._last_wm = wm
        visible, edges = filtered_graph(wm, self._filter)
        self._metrics.configure(text=graph_metrics(wm, visible, edge_count=len(edges)))

        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif not wm.nodes:
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="The World Model has no entities to graph yet.",
                    creates="Nodes appear when notes, goals, or workspace activity is indexed.",
                    next_action="Open World Explorer or create an entity.",
                ),
            )
        else:
            set_surface_state(self._surface_state, kind="data")

        selected = wm.selected_node_id
        if selected:
            self._hint.configure(text=f"Selected: {selected} · double-click to open World Explorer")
        self._graph.apply_snapshot(wm, visible_nodes=visible)
        self._inspector.apply_snapshot(wm)
        self._relationships.apply_snapshot(wm)

    def _on_filters(self, state: NodeFilterState) -> None:
        self._filter = state
        if self._on_filter_change is not None:
            self._on_filter_change(state)
        if self._last_wm is not None:
            self.apply_state(self._last_wm)

    def _select(self, node_id: str) -> None:
        nid = str(node_id)
        if self._on_select is not None:
            self._on_select(nid)
        label = nid
        node_type = ""
        if self._last_wm is not None:
            for node in self._last_wm.nodes:
                if node.node_id == nid:
                    label = node.label or nid
                    node_type = node.node_type
                    break
        if self._on_inspect_select is not None:
            self._on_inspect_select(
                InspectableRef(
                    kind="world_node",
                    ref_id=nid,
                    label=label,
                    payload=(("node_id", nid), ("node_type", node_type)),
                )
            )

    def _activate(self, node_id: str) -> None:
        """Double-click: select then navigate to owning World Explorer workspace."""
        self._select(node_id)
        if self._on_activate is not None:
            self._on_activate(node_id)
        elif self._on_navigate is not None:
            self._on_navigate("world_explorer")


__all__ = ["GraphWorkspaceView"]
