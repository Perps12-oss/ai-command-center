"""Command Center dashboard — the primary operational homepage."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import (
    goal_state_color,
    status_color,
)
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    domain_error_from_snap,
    set_surface_state,
)


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
        self._action_view = "chat"
        self._build()

    def _build(self) -> None:
        # Hero
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        hero_top = ctk.CTkFrame(self._hero, fg_color="transparent")
        hero_top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))

        ctk.CTkLabel(
            hero_top,
            text="Command Center",
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

        hero_bottom = ctk.CTkFrame(self._hero, fg_color="transparent")
        hero_bottom.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        self._summary_label = ctk.CTkLabel(
            hero_bottom,
            text="0 goals · 0 executions · 0 approvals · 0 agents",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._summary_label.pack(side="left")

        self._action_button = ctk.CTkButton(
            hero_bottom,
            text="Open Chat",
            font=T.FONT_BODY,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            height=28,
            width=140,
            command=self._on_action,
        )
        self._action_button.pack(side="right")

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

        top = ctk.CTkFrame(self._system, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))
        ctk.CTkLabel(
            top,
            text="System Awareness",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left")

        body = ctk.CTkFrame(self._system, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure((0, 1), weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Workspace Health
        health_frame = GlassCard(body, fg_color=T.BG_GLASS, border_color=T.GLASS_BORDER)
        health_frame.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        ctk.CTkLabel(
            health_frame,
            text="Workspace Health",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))
        self._health_rows: dict[str, _HealthRow] = {}
        for key in ("provider", "agent", "execution", "goal", "world"):
            row = _HealthRow(health_frame)
            row.pack(fill="x", padx=T.PAD, pady=(0, 4))
            self._health_rows[key] = row

        # Recent Changes
        recent_frame = GlassCard(body, fg_color=T.BG_GLASS, border_color=T.GLASS_BORDER)
        recent_frame.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")
        ctk.CTkLabel(
            recent_frame,
            text="Recent Changes",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))
        self._recent_changes = _RecentChangesFeed(recent_frame)
        self._recent_changes.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def _on_action(self) -> None:
        if self._on_navigate and self._action_view:
            self._on_navigate(self._action_view)
        elif self._on_command:
            self._on_command(str(self._action_button.cget("text")).lower())

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
        if snap is None:
            set_surface_state(
                self._surface_state,
                kind="loading",
                message=article18_loading(
                    status="Status: loading Command Center",
                    what="brain_state, executions, agents, approvals, providers, world_model",
                    next_action="Wait for AppState refresh; then use the Hero action.",
                ),
            )
            return

        now = time.time()
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

        paused_goal = next(
            (g for g in goals if getattr(g, "status", "") == "paused"), None
        )

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

        active_goal_count = sum(1 for g in goals if getattr(g, "status", "") == "active")

        err = domain_error_from_snap(
            snap,
            topic_prefixes=("service.", "app.", "tool."),
        )
        quiet = (
            active_goal_count == 0
            and running_count == 0
            and pending_count == 0
            and agent_count == 0
            and mutation_count == 0
        )
        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif quiet:
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="Command Center has no active goals, executions, agents, or approvals yet.",
                    creates="Activity appears when goals run, executions start, "
                    "agents spawn, or approvals are requested.",
                    next_action="Click New Goal or Open Chat from the Hero to begin.",
                ),
            )
        else:
            set_surface_state(self._surface_state, kind="data")

        # Update hero
        self._status_label.configure(
            text=goal_status.title() if goal_status else "Ready",
            text_color=goal_state_color(goal_status)[0],
        )
        self._goal_label.configure(text=active_goal or "No active goal")
        self._summary_label.configure(
            text=f"{active_goal_count} active goal{'s' if active_goal_count != 1 else ''} · "
            f"{running_count} running execution{'s' if running_count != 1 else ''} · "
            f"{pending_count} pending approval{'s' if pending_count != 1 else ''} · "
            f"{agent_count} active agent{'s' if agent_count != 1 else ''}"
        )

        action_view, action_text, action_color = self._resolve_hero_action(
            pending_count, paused_goal, active_goal
        )
        self._action_view = action_view
        self._action_button.configure(
            text=action_text,
            fg_color=action_color,
            hover_color=action_color,
        )

        # Update ops cards
        last_ts = getattr(snap, "last_event_timestamp", 0.0) or now
        exec_ts = last_ts
        if execution_lib and execution_lib.last_run:
            exec_ts = execution_lib.last_run.created_at or exec_ts

        self._ops_cards["executions"].update(
            metric=str(running_count if running_count else total_count),
            status="running" if running_count else "ready",
            sub=f"{total_count} total",
            timestamp=exec_ts,
        )
        self._ops_cards["agents"].update(
            metric=str(agent_count),
            status="running" if agent_count else "ready",
            sub="active" if agent_count else "none",
            timestamp=last_ts,
        )
        self._ops_cards["approvals"].update(
            metric=str(pending_count),
            status="running" if pending_count else "ready",
            sub="pending" if pending_count else "none",
            timestamp=last_ts,
        )
        self._ops_cards["providers"].update(
            metric=str(healthy_count),
            status="ready" if healthy_count else "offline",
            sub=f"{provider_total} total",
            timestamp=last_ts,
        )

        # Update workspace health
        provider_state = "ready"
        if provider_total == 0:
            provider_state = "offline"
        elif healthy_count < provider_total:
            provider_state = "degraded" if healthy_count > 0 else "offline"

        self._health_rows["provider"].update(
            "Providers", f"{healthy_count} / {provider_total} healthy", provider_state
        )
        self._health_rows["agent"].update(
            "Agents", f"{agent_count} active", "running" if agent_count else "ready"
        )
        self._health_rows["execution"].update(
            "Executions",
            f"{running_count} running / {total_count} total",
            "running" if running_count else "ready",
        )
        self._health_rows["goal"].update(
            "Goals",
            f"{active_goal_count} active / {len(goals)} total",
            "running" if active_goal_count else "ready",
        )
        self._health_rows["world"].update(
            "World Model",
            f"{node_count} entities / {edge_count} edges / {mutation_count} mutations",
            "running" if mutation_count else "ready",
        )

        # Update recent changes feed
        self._recent_changes.update_from_snap(snap)

    def _resolve_hero_action(
        self,
        pending_count: int,
        paused_goal: Any,
        active_goal: str,
    ) -> tuple[str, str, str]:
        """Return (view_id, button_text, color) for the primary hero action."""
        if pending_count > 0:
            return "approvals", "Review Approval", T.APPROVAL_ORANGE
        if paused_goal is not None:
            return "goals", "Resume Goal", T.GOAL_AMBER
        if active_goal:
            return "chat", "Open Chat", T.HERO_CYAN
        return "goals", "New Goal", T.GOAL_AMBER


class _OpsCard(ctk.CTkFrame):
    """Operational card: header, metric, status, timestamp, action."""

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
            text="ready",
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
        self._sub.pack(fill="x", padx=T.PAD, pady=(0, 2))

        self._updated = ctk.CTkLabel(
            self,
            text="Updated —",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._updated.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        if command is not None:
            self.bind("<Button-1>", lambda _e: self._on_click())
            for child in self.winfo_children():
                for widget in self._iter_bindable(child):
                    widget.bind("<Button-1>", lambda _e: self._on_click())
            self.configure(cursor="hand2")

    def _iter_bindable(self, widget: Any):
        """Yield a widget and its children for event binding."""
        yield widget
        try:
            for child in widget.winfo_children():
                yield from self._iter_bindable(child)
        except Exception:
            pass

    def _on_click(self) -> None:
        if self._command is not None:
            self._command()

    def update(self, metric: str, status: str, sub: str, timestamp: float) -> None:
        self._metric.configure(text=metric)
        self._sub.configure(text=sub)
        status_text = (status or "ready").strip().lower()
        self._status.configure(text=status_text, text_color=status_color(status_text))
        self._updated.configure(text=f"Updated {_format_relative(timestamp)}")


class _HealthRow(ctk.CTkFrame):
    """Single row in the Workspace Health panel."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self._label = ctk.CTkLabel(
            self, text="", font=T.FONT_BODY, text_color=T.TEXT_PRIMARY, anchor="w"
        )
        self._label.pack(side="left")
        self._status = ctk.CTkLabel(
            self, text="●", font=T.FONT_SMALL, text_color=T.STATUS_READY
        )
        self._status.pack(side="right")

    def update(self, label: str, detail: str, state: str) -> None:
        self._label.configure(text=f"{label}: {detail}")
        self._status.configure(text_color=status_color(state))


class _RecentChangesFeed(ctk.CTkFrame):
    """Scrollable-ish list of the last 10 mutations, executions, approvals, goal transitions."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self._items: list[ctk.CTkLabel] = []
        for _ in range(10):
            lbl = ctk.CTkLabel(
                self,
                text="",
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                justify="left",
            )
            lbl.pack(fill="x", pady=(0, 2))
            self._items.append(lbl)

    def update_from_snap(self, snap: Any) -> None:
        events: list[tuple[float, str, str]] = []

        world_model = getattr(snap, "world_model", None)
        if world_model:
            for m in getattr(world_model, "mutation_log", ())[:10]:
                ts = _parse_timestamp(getattr(m, "timestamp", ""))
                summary = getattr(m, "summary", "")
                events.append((ts, f"Mutation: {summary}" if summary else "Mutation", "world"))

        execution_lib = getattr(snap, "execution_library", None)
        if execution_lib:
            for run in getattr(execution_lib, "run_history", ())[:10]:
                ts = getattr(run, "created_at", 0.0) or 0.0
                summary = getattr(run, "summary", "")
                events.append((ts, f"Execution: {summary}" if summary else "Execution", "execution"))

        permission = getattr(snap, "permission_snapshot", None)
        if permission:
            for check in getattr(permission, "resolved", ())[:10]:
                summary = getattr(check, "summary", "")
                granted = getattr(check, "granted", False)
                verdict = "granted" if granted else "denied"
                events.append((0.0, f"Approval {verdict}: {summary}", "approval"))

        brain_state = getattr(snap, "brain_state", None)
        if brain_state:
            for g in getattr(brain_state, "recent_goals", ())[:10]:
                ts = getattr(g, "updated_at", 0.0) or 0.0
                text = getattr(g, "text", "")
                status = getattr(g, "status", "")
                events.append((ts, f"Goal {status}: {text}" if status else f"Goal: {text}", "goal"))

        events.sort(key=lambda x: x[0], reverse=True)
        if not events:
            empty = article18_empty(
                why="No recent mutations, executions, approvals, or goal transitions yet.",
                creates="Activity appears when goals run, executions complete, "
                "approvals resolve, or the World Model mutates.",
                next_action="Open Goals or Chat to start work that produces changes.",
            )
            self._items[0].configure(text=empty, text_color=T.TEXT_MUTED)
            for lbl in self._items[1:]:
                lbl.configure(text="", text_color=T.TEXT_SECONDARY)
            return

        for i, lbl in enumerate(self._items):
            if i < len(events):
                ts, text, source = events[i]
                prefix = "●" if source == "world" else "›"
                color = {
                    "world": T.WORLD_TEAL,
                    "execution": T.ACCENT_DEFAULT,
                    "approval": T.APPROVAL_ORANGE,
                    "goal": T.GOAL_AMBER,
                }.get(source, T.TEXT_SECONDARY)
                when = _format_relative(ts) if ts > 0 else "—"
                lbl.configure(text=f"{prefix} {text} ({when})", text_color=color)
            else:
                lbl.configure(text="", text_color=T.TEXT_SECONDARY)


def _format_relative(timestamp: float) -> str:
    """Return a human-friendly relative time string."""
    if timestamp <= 0:
        return "—"
    delta = time.time() - timestamp
    if delta < 1:
        return "just now"
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta / 60)}m ago"
    if delta < 86400:
        return f"{int(delta / 3600)}h ago"
    return f"{int(delta / 86400)}d ago"


def _parse_timestamp(value: Any) -> float:
    """Best-effort parse of an ISO or float timestamp."""
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return 0.0
    try:
        return float(value)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except Exception:
        return 0.0
