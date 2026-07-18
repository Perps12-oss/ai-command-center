"""World Model workspace — Article 12 operational surface (Phase 11B).

Architecture contract:
- Pure renderer. Reads AppState via apply_state(snapshot) only.
- No mutable state listeners, repositories, or services.
- Publishes intents through callbacks (WORLD_MODEL_NODE_SELECTED / ENTITY_CREATE_REQUEST).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.world_model_snapshot import WorldModelSnapshot
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    domain_error_from_snap,
    set_surface_state,
)
from ai_command_center.ui.views.world_model import (
    EntityExplorerPanel,
    KnowledgeGraphPanel,
    MutationJournalPanel,
    RelationshipExplorerPanel,
    SelectionInspectorPanel,
)


class WorldExplorerView(ctk.CTkFrame):
    """World Model workspace orchestration shell (Hero + five Article 12 panels)."""

    def __init__(
        self,
        master: Any,
        *,
        on_select: Callable[[str], None] | None = None,
        on_create_entity: Callable[[], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP)
        self._on_select = on_select
        self._on_create_entity = on_create_entity
        self._on_navigate = on_navigate
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.WORLD_TEAL)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        hero_top = ctk.CTkFrame(self._hero, fg_color="transparent")
        hero_top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            hero_top,
            text="World Model",
            font=T.FONT_TITLE,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")
        self._hero_state = ctk.CTkLabel(
            hero_top,
            text="0 entities, 0 relationships",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._hero_state.pack(side="right")

        hero_bottom = ctk.CTkFrame(self._hero, fg_color="transparent")
        hero_bottom.pack(fill="x", padx=T.PAD, pady=(8, T.PAD))
        self._hero_goals = ctk.CTkLabel(
            hero_bottom,
            text="0 active goals",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._hero_goals.pack(side="left")
        self._new_entity_btn = ctk.CTkButton(
            hero_bottom,
            text="New Entity",
            font=T.FONT_BODY,
            fg_color=T.WORLD_TEAL,
            hover_color=T.HERO_CYAN_DIM,
            text_color=T.TEXT_PRIMARY,
            height=28,
            width=120,
            command=self._create_entity,
        )
        self._new_entity_btn.pack(side="right")

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

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=2)
        body.grid_rowconfigure(1, weight=2)
        body.grid_rowconfigure(2, weight=1)

        self._graph = KnowledgeGraphPanel(body, on_select=self._select)
        self._graph.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        self._explorer = EntityExplorerPanel(body, on_select=self._select)
        self._explorer.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=(0, 8))
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._inspector = SelectionInspectorPanel(right)
        self._inspector.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self._relationships = RelationshipExplorerPanel(right, on_select=self._select)
        self._relationships.grid(row=1, column=0, sticky="nsew")

        self._journal = MutationJournalPanel(body)
        self._journal.grid(row=2, column=0, columnspan=2, sticky="nsew")

    def apply_state(self, snapshot: AppState | WorldModelSnapshot | None) -> None:
        """Project AppState (or WorldModelSnapshot) into all panels."""
        if snapshot is None:
            set_surface_state(
                self._surface_state,
                kind="loading",
                message=article18_loading(
                    status="Status: loading World Model",
                    what="world_model nodes, edges, and mutation journal",
                    next_action="Wait for AppState refresh; then create or select an entity.",
                ),
            )
            return
        if isinstance(snapshot, WorldModelSnapshot):
            wm = snapshot
            err = ""
        else:
            wm = snapshot.world_model
            err = domain_error_from_snap(
                snapshot,
                topic_prefixes=("world_model.", "world."),
            )
        edge_count = len(wm.edges)
        entity_count = wm.node_count or len(wm.nodes)
        goals = len(wm.active_goals)
        self._hero_state.configure(
            text=f"{entity_count} entities, {edge_count} relationships"
        )
        self._hero_goals.configure(text=f"{goals} active goals")

        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif entity_count == 0:
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="The World Model has no entities yet.",
                    creates="Entities appear when notes, goals, or workspace activity "
                    "is indexed into the graph.",
                    next_action="Click New Entity or open Goals/Chat to create linked work.",
                ),
            )
        else:
            set_surface_state(self._surface_state, kind="data")

        self._graph.apply_snapshot(wm)
        self._explorer.apply_snapshot(wm)
        self._inspector.apply_snapshot(wm)
        self._relationships.apply_snapshot(wm)
        self._journal.apply_snapshot(wm)

    def _select(self, node_id: str) -> None:
        if self._on_select:
            self._on_select(node_id)

    def _create_entity(self) -> None:
        if self._on_create_entity:
            self._on_create_entity()
