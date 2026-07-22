"""Insights Placeholder — reserved Phase 10+ workspace (PR-UI-E13).

Architecture contract:
- Pure renderer. Reads AppState.insights_state via apply_state only.
- Informative Article 18 empty state (not bare "No Data").
- No analytics engine in this slice.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.core.state.insights_state import InsightsSnapshot
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    set_surface_state,
)


class InsightsView(ctk.CTkFrame):
    """Stub Insights workspace with Phase 10 placeholder messaging."""

    def __init__(
        self,
        master: Any,
        *,
        on_refresh: Callable[[], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_refresh = on_refresh
        self._on_navigate = on_navigate
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.HERO_CYAN)
        self._hero.pack(fill="x", padx=T.PAD, pady=T.PAD)

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            top,
            text="Insights",
            font=T.FONT_TITLE,
            text_color=T.HERO_CYAN,
            anchor="w",
        ).pack(side="left")
        self._revision = ctk.CTkLabel(
            top,
            text="rev 0",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._revision.pack(side="right")

        self._subtitle = ctk.CTkLabel(
            self._hero,
            text="Phase 10+ analytics workspace (placeholder).",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._subtitle.pack(fill="x", padx=T.PAD, pady=(8, 4))

        actions = ctk.CTkFrame(self._hero, fg_color="transparent")
        actions.pack(fill="x", padx=T.PAD, pady=(0, 8))
        if self._on_refresh is not None:
            ctk.CTkButton(
                actions,
                text="Refresh",
                width=100,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.HERO_CYAN_DIM,
                command=self._on_refresh,
            ).pack(side="left", padx=(0, 8))
        if self._on_navigate is not None:
            ctk.CTkButton(
                actions,
                text="Open Evidence",
                width=120,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.HERO_CYAN,
                command=lambda: self._on_navigate("evidence"),
            ).pack(side="left")

        self._surface_state = ctk.CTkLabel(
            self._hero,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self._surface_state.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        self._body = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        self._body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        self._detail = ctk.CTkLabel(
            self._body,
            text="",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="nw",
            justify="left",
            wraplength=720,
        )
        self._detail.pack(fill="both", expand=True, padx=T.PAD, pady=T.PAD)

        # Initial empty projection before first apply_state.
        self.apply_state(None)

    def apply_state(self, snapshot: AppState | InsightsSnapshot | None) -> None:
        if snapshot is None:
            set_surface_state(
                self._surface_state,
                kind="loading",
                message=article18_loading(
                    status="Status: loading Insights",
                    what="insights_state placeholder projection",
                    next_action="Wait for AppState refresh, then revisit this workspace.",
                ),
            )
            self._detail.configure(text="")
            return

        if isinstance(snapshot, InsightsSnapshot):
            insights = snapshot
        elif isinstance(snapshot, AppState):
            insights = snapshot.insights_state
        else:
            return

        self._revision.configure(text=f"rev {insights.revision}")
        selected = insights.selected_insight_id.strip()
        detail_lines = [insights.message]
        if selected:
            detail_lines.append(f"Selected: {selected}")
        self._detail.configure(text="\n\n".join(detail_lines))

        set_surface_state(
            self._surface_state,
            kind="empty",
            message=article18_empty(
                why="Insights are reserved for a later Phase 10+ delivery.",
                creates=(
                    "Summaries will appear when goal, agent, evidence, "
                    "and world-model activity is aggregated here."
                ),
                next_action="Use Evidence, Operations, or World Model for current signals.",
            ),
        )


__all__ = ["InsightsView"]
