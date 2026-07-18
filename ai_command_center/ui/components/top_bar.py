"""Top bar — glass strip continuous with sidebar."""

from __future__ import annotations

import datetime
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.providers.defaults import provider_display_name
from ai_command_center.ui.components.status_pill import StatusPill
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import (
    goal_state_color,
    kernel_state_color,
    status_badge,
)


class TopBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_settings,
        on_close,
        on_navigate: Callable | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            height=T.TOP_BAR_HEIGHT,
            fg_color="transparent",
            border_width=0,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._on_navigate = on_navigate

        # Left: title and active goal
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=(T.PAD, 0), pady=6)

        ctk.CTkLabel(
            left,
            text="◇ AI Command Center",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        ).pack(side="left")

        self._active_goal_btn = ctk.CTkButton(
            left,
            text="No active goal",
            font=T.FONT_SMALL,
            fg_color="transparent",
            hover_color=T.LIGHT_GLASS,
            text_color=goal_state_color("ready")[0],
            height=28,
            command=self._on_active_goal,
        )
        self._active_goal_btn.pack(side="left", padx=(12, 0))

        # Center: operational status pills
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.pack(side="left", expand=True, padx=T.PAD, pady=10)

        self._kernel_pill = StatusPill(center, "Ready", state="ready")
        self._kernel_pill.pack(side="left", padx=(0, 6))

        self._agents_pill = StatusPill(
            center,
            "0 agents",
            state="ready",
            command=self._on_agents,
        )
        self._agents_pill.pack(side="left", padx=(0, 6))

        self._approvals_pill = StatusPill(
            center,
            "0 pending",
            state="ready",
            command=self._on_approvals,
        )
        self._approvals_pill.pack(side="left", padx=(0, 6))

        self._model_pill = StatusPill(
            center,
            "llama3.2:3b",
            state="ready",
            command=self._on_model,
        )
        self._model_pill.pack(side="left", padx=(0, 6))

        self._provider_pill = StatusPill(
            center,
            "Provider",
            state="ready",
            command=self._on_providers,
        )
        self._provider_pill.pack(side="left", padx=(0, 6))

        # Right: time, settings, close
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=(0, T.PAD), pady=10)

        self._time_label = ctk.CTkLabel(
            right,
            text="--:--",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._time_label.pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            right,
            text="⚙",
            width=36,
            height=36,
            font=T.FONT_BODY,
            fg_color=T.GLASS_BG,
            hover_color=T.GLASS_BORDER,
            border_width=0,
            command=on_settings,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            right,
            text="✕",
            width=36,
            height=36,
            font=T.FONT_BODY,
            fg_color=T.GLASS_BG,
            hover_color=T.STATUS_ERROR,
            border_width=0,
            command=on_close,
        ).pack(side="right", padx=4)

        self._update_time()

    def _on_active_goal(self) -> None:
        if self._on_navigate:
            self._on_navigate("goals")

    def _on_agents(self) -> None:
        if self._on_navigate:
            self._on_navigate("agents")

    def _on_approvals(self) -> None:
        if self._on_navigate:
            self._on_navigate("approvals")

    def _on_model(self) -> None:
        if self._on_navigate:
            self._on_navigate("providers")

    def _on_providers(self) -> None:
        if self._on_navigate:
            self._on_navigate("providers")

    def _update_time(self) -> None:
        try:
            now = datetime.datetime.now()
            self._time_label.configure(text=now.strftime("%H:%M"))
            self.after(1000, self._update_time)
        except Exception:
            pass

    def update_status(self, phase: str, model: str) -> None:
        if model:
            self._model_pill.set_state(model, "ready")

    def update_llm_status(
        self,
        *,
        provider: str,
        phase: str,
        model: str,
        ollama_online: bool,
        openai_online: bool,
        openai_configured: bool,
    ) -> None:
        """Reflect active provider, model, and connection health in the top bar."""
        self.update_status(phase, model)
        provider_name = provider_display_name(provider)
        self._provider_pill.set_state(provider_name, "ready")

        if phase in {"starting", "busy"}:
            self._provider_pill.set_state(provider_name, status_badge("busy"))
            return
        if phase in {"error", "stopped"}:
            self._provider_pill.set_state(provider_name, status_badge("error"))
            return

        if provider == "openai":
            if not openai_configured:
                self._provider_pill.set_state("No API key", status_badge("offline"))
            elif openai_online:
                self._provider_pill.set_state(provider_name, status_badge("ready"))
            else:
                self._provider_pill.set_state("Offline", status_badge("offline"))
            return

        if ollama_online:
            self._provider_pill.set_state(provider_name, status_badge("ready"))
        else:
            self._provider_pill.set_state("Offline", status_badge("offline"))

    def update_top_bar(self, snap: Any) -> None:
        """Project AppState operational summary into the top bar."""
        brain_state = getattr(snap, "brain_state", None)

        # Active goal
        goals = list(getattr(brain_state, "recent_goals", ()) if brain_state else ())
        active_goal = ""
        goal_state = "ready"
        for g in goals:
            status = getattr(g, "status", "")
            if status in {"active", "queued", "running"}:
                active_goal = getattr(g, "text", "")
                goal_state = status
                break
        self._active_goal_btn.configure(
            text=active_goal or "No active goal",
            text_color=goal_state_color(goal_state)[0],
        )

        # Kernel state
        kernel_state = getattr(brain_state, "kernel_state", "") if brain_state else ""
        self._kernel_pill.set_state(
            kernel_state.title() or "Ready",
            kernel_state_color(kernel_state),
        )

        # Active agents
        agent_pipeline = getattr(snap, "agent_pipeline", None)
        agent_count = len(
            getattr(agent_pipeline, "active_run_ids", ()) if agent_pipeline else ()
        )
        self._agents_pill.set_state(
            f"{agent_count} agent{'s' if agent_count != 1 else ''}",
            "running" if agent_count else "ready",
        )

        # Pending approvals
        permission = getattr(snap, "permission_snapshot", None)
        pending_count = 1 if (permission and permission.has_pending) else 0
        self._approvals_pill.set_state(
            f"{pending_count} pending",
            "running" if pending_count else "ready",
        )

    def set_ollama_online(self, online: bool) -> None:
        """Backward-compatible hook for legacy Ollama-only updates."""
        if online:
            self._provider_pill.set_state("Ollama", "ready")
        else:
            self._provider_pill.set_state("Ollama offline", "offline")


