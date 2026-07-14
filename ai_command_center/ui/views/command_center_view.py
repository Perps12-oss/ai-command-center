"""Command Center dashboard — the primary operational homepage."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T


class CommandCenterView(ctk.CTkFrame):
    """Mission Control dashboard: Hero, Operations Grid, System Awareness."""

    def __init__(
        self,
        master,
        on_command: Callable[[str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_command = on_command
        self._on_navigate = on_navigate
        self._build()

    def _build(self) -> None:
        # Hero
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        hero_top = ctk.CTkFrame(self._hero, fg_color="transparent")
        hero_top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))

        ctk.CTkLabel(
            hero_top,
            text="AI Command Center",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        self._status_label = ctk.CTkLabel(
            hero_top,
            text="Ready",
            font=T.FONT_HEADER,
            text_color=T.STATUS_READY,
        )
        self._status_label.pack(side="right")

        self._goal_label = ctk.CTkLabel(
            self._hero,
            text="No active goal",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._goal_label.pack(fill="x", padx=T.PAD, pady=(8, 0))

        self._summary_label = ctk.CTkLabel(
            self._hero,
            text="0 goals · 0 executions · 0 approvals · 0 agents",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._summary_label.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # Operations Grid
        ops = ctk.CTkFrame(self, fg_color="transparent")
        ops.pack(fill="x", padx=T.PAD, pady=(8, 8))
        ops.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._ops_cards: dict[str, _OpsCard] = {}
        for col, (key, title, color) in enumerate(
            (
                ("executions", "Executions", T.ACCENT_DEFAULT),
                ("agents", "Agents", T.AGENT_PURPLE),
                ("approvals", "Approvals", T.APPROVAL_ORANGE),
                ("providers", "Providers", T.HERO_CYAN),
            )
        ):
            card = _OpsCard(ops, title, color, command=lambda k=key: self._on_card_click(k))
            card.grid(row=0, column=col, padx=(0 if col == 0 else 8, 0), pady=0, sticky="nsew")
            self._ops_cards[key] = card

        # System Awareness
        self._system = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        self._system.pack(fill="both", expand=True, padx=T.PAD, pady=(8, T.PAD))

        self._system_label = ctk.CTkLabel(
            self._system,
            text="World Model",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._system_label.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._system_detail = ctk.CTkLabel(
            self._system,
            text="0 entities · 0 relationships · 0 mutations",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._system_detail.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        self._recent_label = ctk.CTkLabel(
            self._system,
            text="No recent changes",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._recent_label.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

    def _on_card_click(self, key: str) -> None:
        if self._on_navigate:
            mapping = {
                "executions": "executions",
                "agents": "agents",
                "approvals": "approvals",
                "providers": "providers",
            }
            self._on_navigate(mapping.get(key, "command_center"))
        elif self._on_command:
            mapping = {
                "executions": "show executions",
                "agents": "show agents",
                "approvals": "show approvals",
                "providers": "show providers",
            }
            self._on_command(mapping.get(key, ""))

    def apply_state(self, snap: Any) -> None:
        """Project AppState into the dashboard."""
        brain_state = getattr(snap, "brain_state", None)
        goals = list(getattr(brain_state, "recent_goals", ()) if brain_state else ())
        active_goal = ""
        goal_status = "ready"
        for g in goals:
            status = getattr(g, "status", "")
            if status in {"active", "queued", "running"}:
                active_goal = getattr(g, "text", "")
                goal_status = status
                break
        if not active_goal and goals:
            active_goal = getattr(goals[0], "text", "")
            goal_status = getattr(goals[0], "status", "")

        execution_lib = getattr(snap, "execution_library", None)
        active_plan = getattr(execution_lib, "active_plan", None) if execution_lib else None
        running_count = 1 if (active_plan and active_plan.is_active) else 0
        total_count = getattr(execution_lib, "total_runs", 0) if execution_lib else 0

        agent_pipeline = getattr(snap, "agent_pipeline", None)
        agent_count = len(getattr(agent_pipeline, "active_run_ids", ()) if agent_pipeline else ())

        permission = getattr(snap, "permission_snapshot", None)
        pending_count = 1 if (permission and permission.has_pending) else 0

        provider_registry = getattr(snap, "provider_registry", None)
        healthy_count = getattr(provider_registry, "healthy_count", 0) if provider_registry else 0
        provider_total = getattr(provider_registry, "total_count", 0) if provider_registry else 0

        world_model = getattr(snap, "world_model", None)
        node_count = getattr(world_model, "node_count", 0) if world_model else 0
        edge_count = len(getattr(world_model, "edges", ())) if world_model else 0
        mutation_count = getattr(world_model, "mutation_count", 0) if world_model else 0
        mutation_log = getattr(world_model, "mutation_log", ()) if world_model else ()

        # Update hero
        self._status_label.configure(text=goal_status.title() if goal_status else "Ready")
        self._status_label.configure(text_color=_status_color(goal_status))
        self._goal_label.configure(text=active_goal or "No active goal")
        active_goal_count = sum(1 for g in goals if getattr(g, "status", "") == "active")
        self._summary_label.configure(
            text=f"{active_goal_count} active goal{'s' if active_goal_count != 1 else ''} · "
                 f"{running_count} running execution{'s' if running_count != 1 else ''} · "
                 f"{pending_count} pending approval{'s' if pending_count != 1 else ''} · "
                 f"{agent_count} active agent{'s' if agent_count != 1 else ''}"
        )

        # Update ops cards
        self._ops_cards["executions"].update(
            metric=str(running_count if running_count else total_count),
            status="running" if running_count else "ready",
            sub=f"{total_count} total",
        )
        self._ops_cards["agents"].update(
            metric=str(agent_count),
            status="running" if agent_count else "ready",
            sub="active" if agent_count else "none",
        )
        self._ops_cards["approvals"].update(
            metric=str(pending_count),
            status="running" if pending_count else "ready",
            sub="pending" if pending_count else "none",
        )
        self._ops_cards["providers"].update(
            metric=str(healthy_count),
            status="ready" if healthy_count else "offline",
            sub=f"{provider_total} total",
        )

        # Update system awareness
        self._system_detail.configure(
            text=f"{node_count} entities · {edge_count} relationships · {mutation_count} mutations"
        )
        if mutation_log:
            last = mutation_log[0]
            summary = getattr(last, "summary", "")
            self._recent_label.configure(text=f"Latest: {summary}" if summary else "No recent changes")
        else:
            self._recent_label.configure(text="No recent changes — mutations appear here")


class _OpsCard(ctk.CTkFrame):
    """Operational card: header, metric, status, action."""

    def __init__(self, master, title: str, color: str, command: Callable[[], None] | None = None) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=T.GLASS_BORDER,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
        )
        self._command = command
        self._color = color

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 2))
        ctk.CTkLabel(
            top,
            text=title.upper(),
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
        ).pack(side="left")

        self._status = ctk.CTkLabel(
            top,
            text="●",
            font=T.FONT_SMALL,
            text_color=T.STATUS_READY,
        )
        self._status.pack(side="right")

        self._metric = ctk.CTkLabel(
            self,
            text="0",
            font=(T.FONT_FAMILY, 28, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._metric.pack(fill="x", padx=T.PAD, pady=(0, 2))

        self._sub = ctk.CTkLabel(
            self,
            text="—",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._sub.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        if command is not None:
            self.bind("<Button-1>", lambda _e: self._on_click())
            for child in self.winfo_children():
                child.bind("<Button-1>", lambda _e: self._on_click())
            self.configure(cursor="hand2")

    def _on_click(self) -> None:
        if self._command is not None:
            self._command()

    def update(self, metric: str, status: str, sub: str) -> None:
        self._metric.configure(text=metric)
        self._sub.configure(text=sub)
        self._status.configure(text_color=_status_color(status))


def _status_color(status: str) -> str:
    status = str(status).lower()
    return {
        "ready": T.STATUS_READY,
        "running": T.STATUS_BUSY,
        "busy": T.STATUS_BUSY,
        "waiting": T.STATUS_BUSY,
        "blocked": T.STATUS_BUSY,
        "paused": T.STATUS_BUSY,
        "failed": T.STATUS_ERROR,
        "error": T.STATUS_ERROR,
        "offline": T.TEXT_MUTED,
        "complete": T.STATUS_READY,
    }.get(status, T.TEXT_MUTED)
