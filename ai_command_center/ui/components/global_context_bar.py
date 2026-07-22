"""Global context bar — shell-wide operational context below the top bar."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.core.state.global_context_state import resolve_active_goal
from ai_command_center.providers.defaults import provider_display_name
from ai_command_center.ui.design_system import theme_v2 as T


class GlobalContextBar(ctk.CTkFrame):
    """Displays active goal, workspace/entity, sources, token budget, and model.

    The bar is a read-only projection of :class:`AppState`; it never holds
    authoritative state and only publishes user intent through callbacks.
    """

    def __init__(
        self,
        master: Any,
        *,
        on_entity_click: Any | None = None,
        on_clear_context: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            height=T.CONTEXT_BAR_HEIGHT,
            fg_color=T.CONTEXT_BAR_BG,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._on_entity_click = on_entity_click
        self._on_clear_context = on_clear_context

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=(T.PAD, 0), pady=6)

        ctk.CTkLabel(
            left,
            text="Context",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(0, 8))

        self._goal_label = ctk.CTkLabel(
            left,
            text="No active goal",
            font=T.FONT_SMALL,
            text_color=T.GOAL_AMBER,
        )
        self._goal_label.pack(side="left", padx=(0, 12))

        self._scope_label = ctk.CTkLabel(
            left,
            text="No active workspace",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
        )
        self._scope_label.pack(side="left")

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.pack(side="left", expand=True, padx=T.PAD, pady=6)

        self._sources_label = ctk.CTkLabel(
            center,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._sources_label.pack(side="left")

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=(0, T.PAD), pady=6)

        self._tokens_label = ctk.CTkLabel(
            right,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._tokens_label.pack(side="left", padx=(0, 12))

        self._model_label = ctk.CTkLabel(
            right,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
        )
        self._model_label.pack(side="left", padx=(0, 12))

        self._provider_label = ctk.CTkLabel(
            right,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
        )
        self._provider_label.pack(side="left")

    def update(self, snap: AppState) -> None:
        """Project the current AppState into the bar."""
        ctx = snap.global_context
        settings = snap.settings

        goal_id, goal_title = resolve_active_goal(getattr(snap, "brain_state", None))
        if not goal_title:
            goal_title = ctx.active_goal_title
            goal_id = goal_id or ctx.active_goal_id
        if goal_title:
            self._goal_label.configure(text=f"Goal: {goal_title}")
        elif goal_id:
            self._goal_label.configure(text=f"Goal: {goal_id}")
        else:
            self._goal_label.configure(text="No active goal")

        scope_parts: list[str] = []
        if ctx.workspace_title:
            scope_parts.append(ctx.workspace_title)
        elif ctx.workspace_id:
            scope_parts.append(ctx.workspace_id)
        if ctx.entity_title:
            scope_parts.append(ctx.entity_title)
        elif ctx.entity_id:
            scope_parts.append(ctx.entity_id)
        scope = "  →  ".join(scope_parts) if scope_parts else "No active workspace"
        self._scope_label.configure(text=scope)

        if ctx.sources:
            self._sources_label.configure(text=" · ".join(ctx.sources))
        else:
            self._sources_label.configure(text="No context sources")

        if ctx.token_estimate > 0:
            self._tokens_label.configure(
                text=f"{ctx.token_estimate} tokens",
            )
        else:
            self._tokens_label.configure(text="")

        self._model_label.configure(text=settings.default_model or "")
        self._provider_label.configure(
            text=provider_display_name(settings.provider) or "",
        )


__all__ = ["GlobalContextBar"]
