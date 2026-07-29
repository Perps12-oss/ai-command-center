"""Live Activity Timeline — chronological Mission Control feed."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.surface_state import article18_empty


class ActivityTimeline(GlassCard):
    """First-class chronological feed (Priority 6)."""

    def __init__(self, master, *, max_items: int = 12) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        self._max = max_items

        ctk.CTkLabel(
            self,
            text="Live Timeline",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._host = ctk.CTkFrame(self, fg_color="transparent")
        self._host.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

        self._items: list[ctk.CTkLabel] = []
        for _ in range(max_items):
            lbl = ctk.CTkLabel(
                self._host,
                text="",
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                justify="left",
            )
            lbl.pack(fill="x", pady=(0, 2))
            self._items.append(lbl)

        # Compatibility with CommandCenterView tests that use _recent_changes
        self._recent_alias = self

    def update_from_snap(self, snap: Any) -> None:
        events = collect_timeline_events(snap)
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
                color = {
                    "world": T.WORLD_TEAL,
                    "execution": T.EXECUTION_BLUE,
                    "approval": T.APPROVAL_ORANGE,
                    "goal": T.GOAL_AMBER,
                    "agent": T.AGENT_PURPLE,
                    "planner": T.REASONING_PURPLE,
                    "system": T.TEXT_SECONDARY,
                }.get(source, T.TEXT_SECONDARY)
                when = _format_clock(ts) if ts > 0 else "——"
                lbl.configure(text=f"{when}  {text}", text_color=color)
            else:
                lbl.configure(text="", text_color=T.TEXT_SECONDARY)


def collect_timeline_events(snap: Any) -> list[tuple[float, str, str]]:
    events: list[tuple[float, str, str]] = []
    if snap is None:
        return events

    world_model = getattr(snap, "world_model", None)
    if world_model:
        for m in getattr(world_model, "mutation_log", ())[:10]:
            ts = _parse_timestamp(getattr(m, "timestamp", ""))
            summary = getattr(m, "summary", "")
            events.append(
                (ts, f"Mutation: {summary}" if summary else "Mutation · Workspace updated", "world")
            )

    execution_lib = getattr(snap, "execution_library", None)
    if execution_lib:
        for run in getattr(execution_lib, "run_history", ())[:10]:
            ts = getattr(run, "created_at", 0.0) or 0.0
            summary = getattr(run, "summary", "")
            events.append((ts, f"Execution started · {summary}" if summary else "Execution started", "execution"))
        active = getattr(execution_lib, "active_plan", None)
        if active and getattr(active, "is_active", False):
            events.append((0.0, "Execution running", "execution"))

    timeline = getattr(snap, "execution_timeline", None)
    if timeline:
        for ev in getattr(timeline, "events", ())[:10]:
            ts = float(getattr(ev, "timestamp", 0.0) or 0.0)
            et = str(getattr(ev, "event_type", "") or "event")
            events.append((ts, et.replace("_", " ").title(), "execution"))

    permission = getattr(snap, "permission_snapshot", None)
    if permission:
        for check in getattr(permission, "resolved", ())[:10]:
            summary = getattr(check, "summary", "")
            granted = getattr(check, "granted", False)
            verdict = "granted" if granted else "denied"
            events.append((0.0, f"Approval {verdict}: {summary}", "approval"))
        if getattr(permission, "has_pending", False):
            pending = getattr(permission, "pending", None)
            summary = str(getattr(pending, "summary", "") or "input required")
            events.append((0.0, f"Waiting · {summary}", "approval"))

    brain_state = getattr(snap, "brain_state", None)
    if brain_state:
        for g in getattr(brain_state, "recent_goals", ())[:10]:
            ts = getattr(g, "updated_at", 0.0) or 0.0
            text = getattr(g, "text", "")
            status = getattr(g, "status", "")
            label = "Goal completed" if str(status).lower() in {"complete", "completed", "done"} else f"Goal {status}"
            events.append((ts, f"{label}: {text}" if status else f"Goal: {text}", "goal"))
        plan = getattr(brain_state, "last_plan", None)
        if plan:
            plan_status = str(getattr(plan, "status", "") or "").lower()
            plan_id = str(getattr(plan, "plan_id", "") or "")
            plan_goal = str(getattr(plan, "goal", "") or "")
            if plan_status and plan_status not in {"", "idle", "pending"} and (plan_id or plan_goal):
                events.append(
                    (0.0, f"Planner generated execution · {plan_status}", "planner")
                )

    agent_pipeline = getattr(snap, "agent_pipeline", None)
    if agent_pipeline:
        for run in getattr(agent_pipeline, "runs", ())[:6]:
            task = getattr(run, "task", "") or getattr(run, "agent_id", "agent")
            state = getattr(run, "state", "")
            events.append((0.0, f"Agent {state}: {task}", "agent"))

    events.sort(key=lambda x: x[0], reverse=True)
    return events


def _format_clock(timestamp: float) -> str:
    if timestamp <= 0:
        return "——"
    try:
        return datetime.fromtimestamp(timestamp).strftime("%H:%M")
    except Exception:
        return "——"


def _parse_timestamp(value: Any) -> float:
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
