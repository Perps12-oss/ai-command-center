"""Grouped status strip — Runtime · Planner · Queue · Agents · Model · Providers."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color
from ai_command_center.ui.mission_control.modes import MissionMode, derive_mission_mode


class GroupedStatusStrip(ctk.CTkFrame):
    """Compact Tier-1 awareness strip above the Mission hero."""

    _SLOTS: tuple[str, ...] = (
        "runtime",
        "planner",
        "queue",
        "agents",
        "model",
        "providers",
    )

    def __init__(self, master, *, compact: bool = False) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.GLASS_BORDER,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
            height=36 if compact else 44,
        )
        self.pack_propagate(False)
        self._pills: dict[str, _StatusPill] = {}

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=10, pady=6)

        for i, key in enumerate(self._SLOTS):
            if i > 0:
                ctk.CTkLabel(
                    row,
                    text="·",
                    font=T.FONT_SMALL,
                    text_color=T.TEXT_MUTED,
                    width=12,
                ).pack(side="left")
            pill = _StatusPill(row, key.title())
            pill.pack(side="left", padx=(0, 4))
            self._pills[key] = pill

    def apply_state(self, snap: Any) -> None:
        if snap is None:
            for pill in self._pills.values():
                pill.set("—", "offline")
            return

        mode = derive_mission_mode(snap)
        phase = str(getattr(snap, "phase", "") or "ready").lower()
        system = getattr(snap, "system_snapshot", None)
        ollama = bool(getattr(system, "ollama_online", False)) if system else False

        brain = getattr(snap, "brain_state", None)
        plan = getattr(brain, "last_plan", None) if brain else None
        plan_status = str(getattr(plan, "status", "") or "idle") or "idle"

        queued = 0
        if brain:
            queued = sum(
                1
                for g in getattr(brain, "recent_goals", ())
                if str(getattr(g, "status", "")).lower() in {"queued", "pending"}
            )

        agent_pipeline = getattr(snap, "agent_pipeline", None)
        agents = len(getattr(agent_pipeline, "active_run_ids", ()) if agent_pipeline else ())

        settings = getattr(snap, "settings", None)
        model = str(getattr(settings, "model_name", "") or getattr(settings, "default_model", "") or "—")
        if len(model) > 18:
            model = model[:16] + "…"

        providers = getattr(snap, "provider_registry", None)
        healthy = getattr(providers, "healthy_count", 0) if providers else 0
        total = getattr(providers, "total_count", 0) if providers else 0

        runtime_state = "error" if mode == MissionMode.FAILURE else (
            "running" if mode in {MissionMode.EXECUTING, MissionMode.PLANNING} else (
                "degraded" if phase in {"degraded", "starting"} else "ready"
            )
        )
        self._pills["runtime"].set(
            "healthy" if runtime_state == "ready" else runtime_state,
            runtime_state,
        )
        self._pills["planner"].set(plan_status or "idle", plan_status or "ready")
        self._pills["queue"].set(f"{queued}", "busy" if queued else "ready")
        self._pills["agents"].set(f"{agents}", "running" if agents else "ready")
        self._pills["model"].set(model, "ready" if ollama or model != "—" else "offline")
        provider_state = "ready"
        if total == 0:
            provider_state = "offline"
        elif healthy < total:
            provider_state = "degraded" if healthy else "offline"
        self._pills["providers"].set(f"{healthy}/{total}", provider_state)


class _StatusPill(ctk.CTkFrame):
    def __init__(self, master, label: str) -> None:
        super().__init__(master, fg_color="transparent")
        self._dot = ctk.CTkLabel(
            self, text="●", font=T.FONT_SMALL, text_color=T.STATUS_READY, width=12
        )
        self._dot.pack(side="left")
        self._label = ctk.CTkLabel(
            self,
            text=f"{label}: —",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._label.pack(side="left")
        self._name = label

    def set(self, value: str, state: str) -> None:
        self._dot.configure(text_color=status_color(state))
        self._label.configure(text=f"{self._name}: {value}")
