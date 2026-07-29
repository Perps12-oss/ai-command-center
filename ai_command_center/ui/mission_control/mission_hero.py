"""Mission Control hero — adaptive Current Mission panel (Tier 1)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.mission_control.modes import (
    MissionMode,
    derive_mission_mode,
    mode_color,
    mode_label,
)
from ai_command_center.ui.views.surface_state import (
    article18_empty,
    article18_loading,
    domain_error_from_snap,
    set_surface_state,
)


_IDLE_SUGGESTIONS: tuple[str, ...] = (
    "Organize Downloads",
    "Summarize Clipboard",
    "Search Notes",
    "Build Workflow",
)


class MissionHeroPanel(GlassCard):
    """Dynamic Mission Control hero with Idle / Planning / Executing / Waiting / Failure."""

    def __init__(
        self,
        master,
        *,
        on_navigate: Callable[[str], None] | None = None,
        on_command: Callable[[str], None] | None = None,
        on_primary: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        self._on_navigate = on_navigate
        self._on_command = on_command
        self._on_primary = on_primary
        self._action_view = "goals"
        self._mode = MissionMode.IDLE

        # Compatibility labels expected by projection tests
        hero_top = ctk.CTkFrame(self, fg_color="transparent")
        hero_top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))

        ctk.CTkLabel(
            hero_top,
            text="Current Mission",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        self._status_label = ctk.CTkLabel(
            hero_top,
            text="Idle",
            font=T.FONT_HEADER,
            text_color=T.STATUS_READY,
        )
        self._status_label.pack(side="right")

        self._goal_label = ctk.CTkLabel(
            self,
            text="No active mission",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._goal_label.pack(fill="x", padx=T.PAD, pady=(8, 0))

        self._narrative = ctk.CTkLabel(
            self,
            text="The AI is ready.",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self._narrative.pack(fill="x", padx=T.PAD, pady=(4, 0))

        # Progress bars (shown in active modes)
        self._progress_host = ctk.CTkFrame(self, fg_color="transparent")
        self._progress_host.pack(fill="x", padx=T.PAD, pady=(8, 0))
        self._bars: dict[str, _StageBar] = {}
        for key, title in (
            ("planning", "Planning"),
            ("execution", "Execution"),
            ("verification", "Verification"),
        ):
            bar = _StageBar(self._progress_host, title)
            bar.pack(fill="x", pady=2)
            self._bars[key] = bar

        hero_bottom = ctk.CTkFrame(self, fg_color="transparent")
        hero_bottom.pack(fill="x", padx=T.PAD, pady=(8, 4))

        self._summary_label = ctk.CTkLabel(
            hero_bottom,
            text="Runtime healthy · Planner idle · World Model synchronized · Providers connected",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self._summary_label.pack(side="left", fill="x", expand=True)

        self._actions = ctk.CTkFrame(hero_bottom, fg_color="transparent")
        self._actions.pack(side="right")

        self._secondary_button = ctk.CTkButton(
            self._actions,
            text="Browse Templates",
            font=T.FONT_BODY,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            text_color=T.TEXT_PRIMARY,
            border_width=1,
            border_color=T.GLASS_BORDER,
            height=28,
            width=130,
            command=self._on_secondary,
        )
        self._secondary_button.pack(side="left", padx=(0, 6))

        self._action_button = ctk.CTkButton(
            self._actions,
            text="+ Start a Mission",
            font=T.FONT_BODY,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            height=28,
            width=150,
            command=self._on_action,
        )
        self._action_button.pack(side="left")

        self._suggestions = ctk.CTkFrame(self, fg_color="transparent")
        self._suggestions.pack(fill="x", padx=T.PAD, pady=(0, 4))
        self._suggestion_labels: list[ctk.CTkLabel] = []
        hint = ctk.CTkLabel(
            self._suggestions,
            text="Suggested",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        hint.pack(anchor="w")
        for text in _IDLE_SUGGESTIONS:
            lbl = ctk.CTkLabel(
                self._suggestions,
                text=f"• {text}",
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                cursor="hand2",
            )
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda _e, t=text: self._suggest(t))
            self._suggestion_labels.append(lbl)

        self._surface_state = ctk.CTkLabel(
            self,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self._surface_state.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

    def _on_action(self) -> None:
        if self._on_primary:
            self._on_primary()
            return
        if self._on_navigate and self._action_view:
            self._on_navigate(self._action_view)

    def _on_secondary(self) -> None:
        """Secondary CTA — navigate to the relevant control surface (honest labels)."""
        if self._mode == MissionMode.WAITING and self._on_navigate:
            self._on_navigate("approvals")
        elif self._mode == MissionMode.FAILURE and self._on_navigate:
            self._on_navigate("executions")
        elif self._mode in {MissionMode.EXECUTING, MissionMode.PLANNING} and self._on_navigate:
            self._on_navigate("operations")
        elif self._on_navigate:
            self._on_navigate("automation")

    def _suggest(self, text: str) -> None:
        if self._on_command:
            self._on_command(text)

    def apply_state(self, snap: Any) -> MissionMode:
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
            return MissionMode.IDLE

        mode = derive_mission_mode(snap)
        self._mode = mode

        brain = getattr(snap, "brain_state", None)
        goals = list(getattr(brain, "recent_goals", ()) if brain else ())
        active_goal = ""
        goal_status = "ready"
        paused_goal = None
        for g in goals:
            status = str(getattr(g, "status", "") or "")
            if status in {"active", "queued", "running", "planning"}:
                active_goal = str(getattr(g, "text", "") or "")
                goal_status = status
                break
            if status == "paused":
                paused_goal = g
        if not active_goal and goals:
            active_goal = str(getattr(goals[0], "text", "") or "")
            goal_status = str(getattr(goals[0], "status", "") or "")

        execution_lib = getattr(snap, "execution_library", None)
        active_plan = getattr(execution_lib, "active_plan", None) if execution_lib else None
        progress = float(getattr(active_plan, "progress", 0.0) or 0.0) if active_plan else 0.0
        running = bool(active_plan and getattr(active_plan, "is_active", False))

        agent_pipeline = getattr(snap, "agent_pipeline", None)
        agent_count = len(getattr(agent_pipeline, "active_run_ids", ()) if agent_pipeline else ())

        permission = getattr(snap, "permission_snapshot", None)
        pending = 1 if (permission and getattr(permission, "has_pending", False)) else 0

        providers = getattr(snap, "provider_registry", None)
        healthy = getattr(providers, "healthy_count", 0) if providers else 0
        provider_total = getattr(providers, "total_count", 0) if providers else 0

        world = getattr(snap, "world_model", None)
        mutations = getattr(world, "mutation_count", 0) if world else 0

        active_goal_count = sum(
            1 for g in goals if str(getattr(g, "status", "")) == "active"
        )

        err = domain_error_from_snap(snap, topic_prefixes=("service.", "app.", "tool."))
        quiet = (
            active_goal_count == 0
            and not running
            and pending == 0
            and agent_count == 0
            and mutations == 0
        )
        if err:
            set_surface_state(self._surface_state, kind="error", message=err)
        elif quiet and mode == MissionMode.IDLE:
            set_surface_state(
                self._surface_state,
                kind="empty",
                message=article18_empty(
                    why="Command Center has no active goals, executions, agents, or approvals yet.",
                    creates="Activity appears when goals run, executions start, "
                    "agents spawn, or approvals are requested.",
                    next_action="Click + Start a Mission or use a Suggested action to begin.",
                ),
            )
        else:
            set_surface_state(self._surface_state, kind="data")

        # Always keep operational counts in the summary strip (projection contract).
        running_count = 1 if running else 0
        count_summary = (
            f"{active_goal_count} active goal{'s' if active_goal_count != 1 else ''} · "
            f"{running_count} running execution{'s' if running_count != 1 else ''} · "
            f"{pending} pending approval{'s' if pending != 1 else ''} · "
            f"{agent_count} active agent{'s' if agent_count != 1 else ''}"
        )

        self._status_label.configure(
            text=mode_label(mode),
            text_color=mode_color(mode),
        )
        if active_goal and goal_status.lower() == "active":
            # Preserve goal-status projection used by Command Center tests.
            self._status_label.configure(
                text="Active",
                text_color=mode_color(mode),
            )

        # Mode-specific body
        if mode == MissionMode.IDLE:
            self._goal_label.configure(text="No active mission" if not active_goal else active_goal)
            self._narrative.configure(
                text=(
                    "The AI is ready. "
                    f"Runtime healthy · Planner idle · Providers {healthy}/{provider_total or 0} connected"
                )
            )
            self._summary_label.configure(text=count_summary if not quiet else (
                f"Runtime healthy · Planner idle · World Model synchronized · "
                f"Providers {healthy}/{provider_total or 0} connected"
            ))
            if quiet:
                self._summary_label.configure(text=count_summary)
            self._show_progress(False)
            self._show_suggestions(True)
            self._action_view, action_text, action_color = self._resolve_hero_action(
                pending, paused_goal, active_goal
            )
            if not active_goal and not pending:
                self._action_view = "goals"
                self._action_button.configure(
                    text="+ Start a Mission",
                    fg_color=T.GOAL_AMBER,
                    hover_color=T.GOAL_AMBER,
                )
                self._secondary_button.configure(text="Browse Templates")
            else:
                self._action_button.configure(
                    text=action_text,
                    fg_color=action_color,
                    hover_color=action_color,
                )
                self._secondary_button.configure(text="Browse Templates")
        elif mode == MissionMode.PLANNING:
            self._goal_label.configure(text=active_goal or "Planning…")
            self._narrative.configure(
                text="Reasoning through plan steps and selecting capabilities."
            )
            self._summary_label.configure(text=count_summary)
            self._show_progress(True)
            self._bars["planning"].set(
                1.0 if plan_done(snap) else 0.0,
                "Complete" if plan_done(snap) else "Running",
            )
            self._bars["execution"].set(0.0, "Pending")
            self._bars["verification"].set(0.0, "Pending")
            self._show_suggestions(False)
            self._action_view, action_text, action_color = self._resolve_hero_action(
                pending, paused_goal, active_goal
            )
            self._action_button.configure(
                text=action_text,
                fg_color=action_color,
                hover_color=action_color,
            )
            self._secondary_button.configure(text="Open Operations")
        elif mode == MissionMode.EXECUTING:
            pct = int(progress * 100)
            self._goal_label.configure(
                text=active_goal or str(getattr(active_plan, "goal", "") or "Running")
            )
            self._narrative.configure(text=f"{pct}% complete")
            self._summary_label.configure(text=count_summary)
            self._show_progress(True)
            self._bars["planning"].set(1.0, "Complete")
            self._bars["execution"].set(
                max(progress, 0.15 if running else 0.0),
                "Running" if running else "Idle",
            )
            self._bars["verification"].set(
                0.0 if progress < 1.0 else 1.0,
                "Pending" if progress < 1.0 else "Complete",
            )
            self._show_suggestions(False)
            self._action_view, action_text, action_color = self._resolve_hero_action(
                pending, paused_goal, active_goal
            )
            self._action_button.configure(
                text=action_text,
                fg_color=action_color,
                hover_color=action_color,
            )
            self._secondary_button.configure(text="Open Operations")
        elif mode == MissionMode.WAITING:
            self._goal_label.configure(text=active_goal or "Awaiting input")
            self._narrative.configure(
                text="Approval or operator input required before progress continues."
            )
            self._summary_label.configure(text=count_summary)
            self._show_progress(True)
            self._bars["planning"].set(1.0, "Complete")
            self._bars["execution"].set(progress, "Paused")
            self._bars["verification"].set(0.0, "Pending")
            self._show_suggestions(False)
            self._action_view = "approvals"
            self._action_button.configure(
                text="Review Approval",
                fg_color=T.APPROVAL_ORANGE,
                hover_color=T.APPROVAL_ORANGE,
            )
            self._secondary_button.configure(text="Open Approvals")
        else:  # FAILURE
            err_text = ""
            if active_plan:
                err_text = str(getattr(active_plan, "error", "") or "")
            self._goal_label.configure(text=active_goal or "Failed")
            self._narrative.configure(
                text=err_text or "Diagnostics available — recovery actions suggested below."
            )
            self._summary_label.configure(text=count_summary)
            self._show_progress(True)
            self._bars["planning"].set(1.0, "Complete")
            self._bars["execution"].set(progress, "Failed")
            self._bars["verification"].set(0.0, "Blocked")
            self._show_suggestions(False)
            self._action_view, action_text, action_color = self._resolve_hero_action(
                pending, paused_goal, active_goal
            )
            if not pending and not paused_goal:
                self._action_view = "executions"
                self._action_button.configure(
                    text="Open Executions",
                    fg_color=T.EXECUTION_BLUE,
                    hover_color=T.EXECUTION_BLUE,
                )
            else:
                self._action_button.configure(
                    text=action_text,
                    fg_color=action_color,
                    hover_color=action_color,
                )
            self._secondary_button.configure(text="Open Executions")

        return mode

    def _resolve_hero_action(
        self,
        pending_count: int,
        paused_goal: Any,
        active_goal: str,
    ) -> tuple[str, str, str]:
        if pending_count > 0:
            return "approvals", "Review Approval", T.APPROVAL_ORANGE
        if paused_goal is not None:
            return "goals", "Resume Goal", T.GOAL_AMBER
        if active_goal:
            return "chat", "Open Chat", T.HERO_CYAN
        return "goals", "New Goal", T.GOAL_AMBER

    def _show_progress(self, visible: bool) -> None:
        try:
            if visible:
                self._progress_host.pack(fill="x", padx=T.PAD, pady=(8, 0))
            else:
                self._progress_host.pack_forget()
        except Exception:
            pass

    def _show_suggestions(self, visible: bool) -> None:
        try:
            if visible:
                self._suggestions.pack(fill="x", padx=T.PAD, pady=(0, 4))
            else:
                self._suggestions.pack_forget()
        except Exception:
            pass


def plan_done(snap: Any) -> bool:
    brain = getattr(snap, "brain_state", None)
    plan = getattr(brain, "last_plan", None) if brain else None
    status = str(getattr(plan, "status", "") or "").lower()
    return status in {"ready", "complete", "completed", "planned"}


class _StageBar(ctk.CTkFrame):
    def __init__(self, master, title: str) -> None:
        super().__init__(master, fg_color="transparent")
        self._title = ctk.CTkLabel(
            self,
            text=title,
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            width=90,
            anchor="w",
        )
        self._title.pack(side="left")
        self._track = ctk.CTkProgressBar(
            self,
            height=8,
            progress_color=T.ACCENT_DEFAULT,
            fg_color=T.BG_INPUT,
        )
        self._track.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self._track.set(0)
        self._state = ctk.CTkLabel(
            self,
            text="Pending",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            width=80,
            anchor="e",
        )
        self._state.pack(side="right")

    def set(self, value: float, label: str) -> None:
        clipped = max(0.0, min(1.0, float(value)))
        try:
            self._track.set(clipped)
        except Exception:
            pass
        color = T.STATUS_READY if label.lower() == "complete" else (
            T.STATUS_ERROR if label.lower() in {"failed", "blocked"} else (
                T.EXECUTION_BLUE if label.lower() == "running" else T.STATUS_BUSY
            )
        )
        self._state.configure(text=label, text_color=color)
        try:
            self._track.configure(progress_color=color)
        except Exception:
            pass
