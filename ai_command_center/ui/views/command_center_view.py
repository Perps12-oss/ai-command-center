"""Command Center dashboard — Mission Control for an intelligent OS.

Layout (Priority target):
  Grouped Status → Mission Hero → [Timeline | Brain] → KPIs → [World | Chips]

UI projects AppState only. Commands flow via on_command / on_navigate → EventBus.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import customtkinter as ctk

from ai_command_center.ui.components.docks.execution_timeline_dock import (
    ExecutionTimelineDock,
)
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.mission_control import (
    ActivityTimeline,
    ActionChips,
    BrainSituationPanel,
    GroupedStatusStrip,
    LayoutPrefs,
    MissionHeroPanel,
    StateAwareKpiCard,
    WorldModelWidget,
)
from ai_command_center.ui.mission_control.layout_prefs import DEFAULT_WIDGET_ORDER


class CommandCenterView(ctk.CTkFrame):
    """Mission Control dashboard: adaptive hero, brain, timeline, KPIs."""

    def __init__(
        self,
        master,
        on_command: Callable[[str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        on_prefill: Callable[[str], None] | None = None,
        layout_prefs: LayoutPrefs | None = None,
        on_pause_goal: Callable[[str], None] | None = None,
        on_abort_goal: Callable[[str], None] | None = None,
        on_approve: Callable[[], None] | None = None,
        on_resume_goal: Callable[[str], None] | None = None,
        on_scrub: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_command = on_command
        self._on_navigate = on_navigate
        self._on_prefill = on_prefill
        self._on_pause_goal = on_pause_goal
        self._on_abort_goal = on_abort_goal
        self._on_approve = on_approve
        self._on_resume_goal = on_resume_goal
        self._on_scrub = on_scrub
        self._prefs = layout_prefs or LayoutPrefs()
        self._action_view = "chat"
        self._sections: dict[str, ctk.CTkFrame] = {}
        # Dashboard timeline window: local scrub index + offset into full oldest-first list.
        self._exec_window_offset = 0
        self._exec_window_ids: tuple[str, ...] = ()
        self._local_scrub_index: int | None = None
        self._build()

    def _build(self) -> None:
        compact = self._prefs.is_compact()
        pad = 8 if compact else T.PAD

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Tier 1 — grouped status
        self._status_strip = GroupedStatusStrip(scroll, compact=compact)
        self._status_strip.pack(fill="x", padx=pad, pady=(pad, 6))

        # Tier 1 — Mission hero
        self._hero_panel = MissionHeroPanel(
            scroll,
            on_navigate=self._on_navigate,
            on_command=self._on_command,
            on_primary=self._on_action,
            on_pause=self._on_pause_goal,
            on_abort=self._on_abort_goal,
            on_approve=self._on_approve,
            on_resume=self._on_resume_goal,
        )
        self._hero_panel.pack(fill="x", padx=pad, pady=(0, 8))
        self._sections["hero"] = self._hero_panel
        self._sections["status"] = self._status_strip

        # Compatibility aliases for existing projection tests
        self._hero = self._hero_panel
        self._status_label = self._hero_panel._status_label
        self._goal_label = self._hero_panel._goal_label
        self._summary_label = self._hero_panel._summary_label
        self._action_button = self._hero_panel._action_button
        self._surface_state = self._hero_panel._surface_state

        # Density / progressive disclosure / widget reorder toolbar
        tools = ctk.CTkFrame(scroll, fg_color="transparent")
        tools.pack(fill="x", padx=pad, pady=(0, 6))
        ctk.CTkButton(
            tools,
            text="Compact" if not compact else "Expanded",
            width=90,
            height=24,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            text_color=T.TEXT_SECONDARY,
            border_width=1,
            border_color=T.GLASS_BORDER,
            command=self._toggle_density,
        ).pack(side="right")
        ctk.CTkButton(
            tools,
            text="Advanced ▾" if not self._prefs.show_advanced else "Advanced ▴",
            width=100,
            height=24,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            text_color=T.TEXT_SECONDARY,
            border_width=1,
            border_color=T.GLASS_BORDER,
            command=self._toggle_advanced,
        ).pack(side="right", padx=(0, 6))
        ctk.CTkButton(
            tools,
            text="Layout ▲",
            width=72,
            height=24,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            text_color=T.TEXT_SECONDARY,
            border_width=1,
            border_color=T.GLASS_BORDER,
            command=lambda: self._reorder_focus(-1),
        ).pack(side="left")
        ctk.CTkButton(
            tools,
            text="Layout ▼",
            width=72,
            height=24,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            text_color=T.TEXT_SECONDARY,
            border_width=1,
            border_color=T.GLASS_BORDER,
            command=lambda: self._reorder_focus(1),
        ).pack(side="left", padx=(6, 0))
        self._layout_focus = "mid"
        self._layout_focus_label = ctk.CTkLabel(
            tools,
            text="Reorder: mid",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._layout_focus_label.pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            tools,
            text="Focus→",
            width=64,
            height=24,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            text_color=T.TEXT_SECONDARY,
            border_width=1,
            border_color=T.GLASS_BORDER,
            command=self._cycle_layout_focus,
        ).pack(side="left", padx=(6, 0))

        # Mid band: Timeline | Brain
        mid = ctk.CTkFrame(scroll, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=pad, pady=(0, 8))
        mid.grid_columnconfigure((0, 1), weight=1)
        mid.grid_rowconfigure(0, weight=1)
        self._sections["mid"] = mid

        self._timeline = ActivityTimeline(mid, max_items=10)
        self._timeline.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._recent_changes = self._timeline  # test alias

        self._brain = BrainSituationPanel(mid)
        self._brain.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # KPI row — state-aware cards
        ops = ctk.CTkFrame(scroll, fg_color="transparent")
        ops.pack(fill="x", padx=pad, pady=(0, 8))
        ops.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._sections["kpis"] = ops

        self._ops_cards: dict[str, StateAwareKpiCard] = {}
        for col, (key, title, color) in enumerate(
            (
                ("executions", "Executions", T.EXECUTION_BLUE),
                ("agents", "Agents", T.AGENT_PURPLE),
                ("approvals", "Approvals", T.APPROVAL_ORANGE),
                ("providers", "Providers", T.HERO_CYAN),
            )
        ):
            card = StateAwareKpiCard(
                ops,
                title,
                color,
                command=lambda k=key: self._on_card_click(k),
                compact=compact,
            )
            card.grid(
                row=0,
                column=col,
                padx=(0 if col == 0 else 8, 0),
                pady=0,
                sticky="nsew",
            )
            self._ops_cards[key] = card

        # Lower band: World Model | chips / recommendations
        lower = ctk.CTkFrame(scroll, fg_color="transparent")
        lower.pack(fill="x", padx=pad, pady=(0, 8))
        lower.grid_columnconfigure((0, 1), weight=1)
        self._sections["lower"] = lower

        self._world = WorldModelWidget(lower, on_navigate=self._on_navigate)
        self._world.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        right = ctk.CTkFrame(lower, fg_color=T.BG_PANEL, corner_radius=T.CARD_RADIUS,
                             border_width=1, border_color=T.GLASS_BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(
            right,
            text="Quick Actions",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))
        self._chips = ActionChips(right, on_chip=self._on_chip)
        self._chips.pack(fill="x", padx=T.PAD, pady=(0, 8))
        self._recommend = ctk.CTkLabel(
            right,
            text="Use chips to pre-fill the command bar, or press Ctrl+K for the full palette.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self._recommend.pack(fill="x", padx=T.PAD, pady=(0, 4))
        ctk.CTkButton(
            right,
            text="Open Operations Timeline",
            height=26,
            font=T.FONT_SMALL,
            fg_color=T.EXECUTION_BLUE,
            hover_color=T.EXECUTION_BLUE,
            command=lambda: self._on_navigate("operations") if self._on_navigate else None,
        ).pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))

        # Composed ExecutionTimelineDock (shared primitive with Operations)
        dock_host = ctk.CTkFrame(
            scroll,
            fg_color=T.BG_PANEL,
            corner_radius=T.CARD_RADIUS,
            border_width=1,
            border_color=T.EXECUTION_BLUE,
        )
        dock_host.pack(fill="x", padx=pad, pady=(0, 8))
        self._sections["dock"] = dock_host
        self._exec_dock = ExecutionTimelineDock(
            dock_host,
            on_scrub=self._handle_exec_scrub,
            timeline_height=72,
            show_section_labels=True,
        )
        self._exec_dock.pack(fill="x", padx=4, pady=4)

        # System awareness (health rows) — retained for tests + Tier 3 detail
        self._system = ctk.CTkFrame(
            scroll,
            fg_color=T.BG_PANEL,
            corner_radius=T.CARD_RADIUS,
            border_width=1,
            border_color=T.GLASS_BORDER,
        )
        self._system.pack(fill="x", padx=pad, pady=(0, pad))
        self._sections["system"] = self._system
        ctk.CTkLabel(
            self._system,
            text="System Awareness",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))
        self._health_rows: dict[str, _HealthRow] = {}
        for key in ("provider", "agent", "execution", "goal", "world"):
            row = _HealthRow(self._system)
            row.pack(fill="x", padx=T.PAD, pady=(0, 4))
            self._health_rows[key] = row
        ctk.CTkFrame(self._system, fg_color="transparent", height=8).pack()

        self._scroll = scroll
        self._pad = pad
        self._apply_widget_order()
        if not self._prefs.show_advanced:
            self._system.pack_forget()
            self._sections["dock"].pack_forget()

    def _toggle_density(self) -> None:
        self._prefs.toggle_density()
        mode = "compact" if self._prefs.is_compact() else "expanded"
        self._recommend.configure(text=f"Density set to {mode}. Re-open Dashboard to fully reflow.")

    def _toggle_advanced(self) -> None:
        show = self._prefs.toggle_advanced()
        if show:
            self._apply_widget_order()
        else:
            try:
                self._system.pack_forget()
                self._sections["dock"].pack_forget()
            except Exception:
                pass

    def _cycle_layout_focus(self) -> None:
        order = [w for w in DEFAULT_WIDGET_ORDER if w in {"mid", "kpis", "lower", "dock", "system"}]
        if self._layout_focus not in order:
            self._layout_focus = order[0]
        else:
            idx = order.index(self._layout_focus)
            self._layout_focus = order[(idx + 1) % len(order)]
        self._layout_focus_label.configure(text=f"Reorder: {self._layout_focus}")

    def _reorder_focus(self, direction: int) -> None:
        self._prefs.move_widget(self._layout_focus, direction)
        self._apply_widget_order()
        self._layout_focus_label.configure(text=f"Reorder: {self._layout_focus}")

    def _apply_widget_order(self) -> None:
        """Re-pack reorderable sections according to LayoutPrefs.widget_order."""
        pad = getattr(self, "_pad", T.PAD)
        order = list(self._prefs.widget_order) or list(DEFAULT_WIDGET_ORDER)
        # Always keep status + hero first visually
        fixed = ["status", "hero"]
        movable = [w for w in order if w not in fixed and w in self._sections]
        for wid in DEFAULT_WIDGET_ORDER:
            if wid not in fixed and wid not in movable and wid in self._sections:
                movable.append(wid)
        # Unpack movable
        for wid in movable:
            try:
                self._sections[wid].pack_forget()
            except Exception:
                pass
        for wid in movable:
            if wid in {"dock", "system"} and not self._prefs.show_advanced:
                continue
            frame = self._sections[wid]
            expand = wid == "mid"
            try:
                frame.pack(fill="both" if expand else "x", expand=expand, padx=pad, pady=(0, 8))
            except Exception:
                pass

    def _on_chip(self, payload: str) -> None:
        if self._on_prefill is not None:
            self._on_prefill(payload)
        elif self._on_command is not None and not payload.endswith((" ", "| ")):
            self._on_command(payload)
        elif self._on_command is not None:
            self._on_command(payload.strip())

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
        """Project AppState into the Mission Control dashboard."""
        if snap is None:
            self._hero_panel.apply_state(None)
            self._status_strip.apply_state(None)
            self._brain.apply_state(None)
            self._world.apply_state(None)
            self._timeline.update_from_snap(None)
            self._exec_dock.render([])
            return

        mode = self._hero_panel.apply_state(snap)
        self._action_view = self._hero_panel._action_view
        self._status_strip.apply_state(snap)
        self._brain.apply_state(snap)
        self._world.apply_state(snap)
        self._timeline.update_from_snap(snap)
        self._render_exec_dock(snap)

        now = time.time()
        brain_state = getattr(snap, "brain_state", None)
        goals = list(getattr(brain_state, "recent_goals", ()) if brain_state else ())

        execution_lib = getattr(snap, "execution_library", None)
        active_plan = getattr(execution_lib, "active_plan", None) if execution_lib else None
        running_count = 1 if (active_plan and active_plan.is_active) else 0
        total_count = getattr(execution_lib, "total_runs", 0) if execution_lib else 0

        agent_pipeline = getattr(snap, "agent_pipeline", None)
        agent_count = len(getattr(agent_pipeline, "active_run_ids", ()) if agent_pipeline else ())
        agent_runs = list(getattr(agent_pipeline, "runs", ()) if agent_pipeline else ())
        waiting_agents = sum(
            1 for r in agent_runs if str(getattr(r, "state", "")).lower() in {"waiting", "pending"}
        )
        idle_agents = max(0, len(agent_runs) - agent_count - waiting_agents)

        permission = getattr(snap, "permission_snapshot", None)
        pending_count = 1 if (permission and permission.has_pending) else 0

        provider_registry = getattr(snap, "provider_registry", None)
        healthy_count = getattr(provider_registry, "healthy_count", 0) if provider_registry else 0
        provider_total = getattr(provider_registry, "total_count", 0) if provider_registry else 0

        world_model = getattr(snap, "world_model", None)
        node_count = getattr(world_model, "node_count", 0) if world_model else 0
        edge_count = len(getattr(world_model, "edges", ()) if world_model else ())
        mutation_count = getattr(world_model, "mutation_count", 0) if world_model else 0
        active_goal_count = sum(1 for g in goals if getattr(g, "status", "") == "active")

        last_ts = getattr(snap, "last_event_timestamp", 0.0) or now
        exec_ts = last_ts
        if execution_lib and execution_lib.last_run:
            exec_ts = execution_lib.last_run.created_at or exec_ts

        completed_today = max(0, total_count - running_count)
        queued = sum(
            1 for g in goals if str(getattr(g, "status", "")).lower() in {"queued", "pending"}
        )

        self._ops_cards["executions"].update(
            metric=str(running_count if running_count else total_count),
            status="running" if running_count else "ready",
            sub=f"Running {running_count} · Completed {completed_today} · Queued {queued}",
            timestamp=exec_ts,
            trend="",
        )
        self._ops_cards["agents"].update(
            metric=str(agent_count),
            status="running" if agent_count else "ready",
            sub=f"Running {agent_count} · Waiting {waiting_agents} · Idle {idle_agents}",
            timestamp=last_ts,
            trend="",
        )
        self._ops_cards["approvals"].update(
            metric=str(pending_count),
            status="running" if pending_count else "ready",
            sub="Pending approval" if pending_count else "None pending",
            timestamp=last_ts,
            trend="",
        )
        self._ops_cards["providers"].update(
            metric=str(healthy_count),
            status="ready" if healthy_count else "offline",
            sub=f"Healthy {healthy_count}/{provider_total} · Unavailable {max(0, provider_total - healthy_count)}",
            timestamp=last_ts,
            trend="",
        )

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

        mode_hints = {
            "idle": "Suggested: Organize Downloads · Summarize Clipboard · Search Notes · Build Workflow",
            "planning": "Pause from the hero or open Operations for the plan graph.",
            "executing": "Pause / Abort publish goal control requests; Approvals open Review Approval.",
            "waiting": "Review Approval opens the Approvals surface — decide grant/deny there.",
            "failure": "Abort cancels an active or paused goal; Open Executions for diagnostics.",
        }
        self._recommend.configure(
            text=mode_hints.get(mode.value if hasattr(mode, "value") else str(mode), mode_hints["idle"])
        )

    def _handle_exec_scrub(self, local_index: int) -> None:
        """Map dock-local scrub index back to the full oldest-first event list."""
        self._local_scrub_index = int(local_index)
        global_index = int(local_index) + int(self._exec_window_offset)
        if self._on_scrub is not None:
            self._on_scrub(global_index)

    def _render_exec_dock(self, snap: Any) -> None:
        steps: list[dict[str, Any]] = []
        timeline = getattr(snap, "execution_timeline", None)
        timeline_events = list(getattr(timeline, "events", ()) if timeline else ())
        # execution_timeline.events is oldest-first; recent_execution_events is newest-first.
        if timeline_events:
            events = timeline_events
        else:
            recent = list(getattr(snap, "recent_execution_events", ()) or ())
            events = list(reversed(recent))
        # Show the most recent window on the dashboard (always oldest→newest within window).
        window = list(events)[-24:]
        offset = max(0, len(events) - len(window))
        self._exec_window_offset = offset
        window_ids = tuple(str(getattr(ev, "event_id", "") or "") for ev in window)
        if window_ids != self._exec_window_ids:
            self._exec_window_ids = window_ids
            self._local_scrub_index = None
        for i, ev in enumerate(window):
            label = str(
                getattr(ev, "event_type", None)
                or getattr(ev, "summary", None)
                or getattr(ev, "type", None)
                or f"step-{i}"
            )
            steps.append(
                {
                    "name": label.replace("_", " "),
                    "status": str(getattr(ev, "status", "") or "ready"),
                    "duration_ms": float(getattr(ev, "duration_ms", 0.0) or 0.0),
                    "timestamp": getattr(ev, "timestamp", 0.0) or 0.0,
                    "event_id": str(getattr(ev, "event_id", "") or ""),
                }
            )
        if not steps:
            # Fall back to execution library run history (still scrubber-shaped)
            lib = getattr(snap, "execution_library", None)
            for run in list(getattr(lib, "run_history", ()) if lib else ())[:8]:
                steps.append(
                    {
                        "name": str(getattr(run, "summary", "") or "Execution"),
                        "status": str(getattr(run, "status", "") or "complete"),
                        "duration_ms": float(getattr(run, "duration_ms", 0.0) or 0.0),
                        "timestamp": getattr(run, "created_at", 0.0) or 0.0,
                        "event_id": "",
                    }
                )
            self._exec_window_offset = 0
        scrub_index = self._resolve_exec_scrub_index(snap, steps, window)
        self._exec_dock.render(steps, scrub_index=scrub_index)

    def _resolve_exec_scrub_index(
        self,
        snap: Any,
        steps: list[dict[str, Any]],
        window: list[Any],
    ) -> int:
        """Highlight within the visible window using the same event list we render."""
        if not steps:
            return 0
        if self._local_scrub_index is not None:
            return max(0, min(int(self._local_scrub_index), len(steps) - 1))
        # Prefer matching the scrubber's selected event_id into this window.
        scrub = getattr(snap, "execution_scrubber", None)
        scrub_events = list(getattr(scrub, "events", ()) if scrub else ())
        if scrub_events:
            raw = int(getattr(scrub, "scrub_index", 0) or 0)
            raw = max(0, min(raw, len(scrub_events) - 1))
            selected_id = str(getattr(scrub_events[raw], "event_id", "") or "")
            if selected_id:
                for i, ev in enumerate(window):
                    if str(getattr(ev, "event_id", "") or "") == selected_id:
                        return i
        # Default: most recent step in the visible window.
        return len(steps) - 1


class _HealthRow(ctk.CTkFrame):
    """Single row in the System Awareness panel."""

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
        from ai_command_center.ui.design_system.status_tokens import status_color

        self._label.configure(text=f"{label}: {detail}")
        self._status.configure(text_color=status_color(state))
