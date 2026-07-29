"""World Model summary widget — entities, relationships, contexts, unresolved."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.surface_state import article18_empty


class WorldModelWidget(GlassCard):
    """Tier-2 World Model health snapshot."""

    def __init__(
        self,
        master,
        *,
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, border_color=T.WORLD_TEAL)
        self._on_navigate = on_navigate

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        ctk.CTkLabel(
            top,
            text="World Model",
            font=T.FONT_HEADER,
            text_color=T.WORLD_TEAL,
            anchor="w",
        ).pack(side="left")
        if on_navigate is not None:
            ctk.CTkButton(
                top,
                text="Open",
                width=56,
                height=24,
                font=T.FONT_SMALL,
                fg_color=T.WORLD_TEAL,
                hover_color=T.WORLD_TEAL,
                command=lambda: on_navigate("world_explorer"),
            ).pack(side="right")

        self._workspace = ctk.CTkLabel(
            self,
            text="Workspace",
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._workspace.pack(fill="x", padx=T.PAD, pady=(0, 4))

        self._stats = ctk.CTkLabel(
            self,
            text="Entities 0 · Relationships 0 · Contexts 0 · Unresolved 0",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self._stats.pack(fill="x", padx=T.PAD, pady=(0, 4))

        self._hint = ctk.CTkLabel(
            self,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self._hint.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

    def apply_state(self, snap: Any) -> None:
        if snap is None:
            self._stats.configure(text="Entities — · Relationships — · Contexts — · Unresolved —")
            return

        world = getattr(snap, "world_model", None)
        nodes = getattr(world, "node_count", 0) if world else 0
        edges = len(getattr(world, "edges", ()) if world else ())
        if world and not edges:
            # edges may be empty tuple while counts exist on nodes only
            edges = len(getattr(world, "edges", ()) or ())
        mutations = getattr(world, "mutation_count", 0) if world else 0
        goals = list(getattr(world, "goals", ()) if world else ())
        unresolved = sum(
            1 for g in goals if str(getattr(g, "status", "")).lower() in {"open", "unresolved", "blocked"}
        )
        # Contexts: approximate via global_context sources + distinct node types
        contexts = 0
        gc = getattr(snap, "global_context", None)
        if gc is not None:
            sources = getattr(gc, "sources", ()) or ()
            contexts = len(sources) if sources else (1 if getattr(gc, "workspace_id", "") else 0)
        if contexts == 0 and nodes:
            types = {str(getattr(n, "node_type", "") or "") for n in getattr(world, "nodes", ())}
            contexts = len([t for t in types if t]) or 1

        ws_title = "Workspace"
        if gc is not None:
            title = str(getattr(gc, "workspace_title", "") or "")
            if title:
                ws_title = title

        self._workspace.configure(text=ws_title)
        self._stats.configure(
            text=(
                f"Entities {nodes} · Relationships {edges} · "
                f"Contexts {contexts} · Unresolved {unresolved}"
            )
        )

        if nodes == 0 and edges == 0 and mutations == 0:
            self._hint.configure(
                text=article18_empty(
                    why="World Model has no entities yet.",
                    creates="Entities and relationships appear as the workspace is observed and mutated.",
                    next_action="Open World Model or start a mission that explores the workspace.",
                )
            )
        else:
            self._hint.configure(
                text=f"{mutations} mutation{'s' if mutations != 1 else ''} recorded"
            )
