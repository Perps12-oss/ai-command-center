"""Adaptive Mission Control modes — pure derivation from AppState."""

from __future__ import annotations

from enum import Enum
from typing import Any


class MissionMode(str, Enum):
    """Homepage adaptive modes (Priority 1)."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    FAILURE = "failure"


def derive_mission_mode(snap: Any) -> MissionMode:
    """Derive the adaptive homepage mode from an AppState snapshot.

    Priority: Failure > Waiting > Executing > Planning > Idle.
    """
    if snap is None:
        return MissionMode.IDLE

    brain = getattr(snap, "brain_state", None)
    goals = list(getattr(brain, "recent_goals", ()) if brain else ())
    kernel = str(getattr(brain, "kernel_state", "") or "").lower()
    last_plan = getattr(brain, "last_plan", None) if brain else None
    plan_status = str(getattr(last_plan, "status", "") or "").lower()

    execution_lib = getattr(snap, "execution_library", None)
    active_plan = getattr(execution_lib, "active_plan", None) if execution_lib else None
    exec_status = str(getattr(active_plan, "status", "") or "").lower()
    exec_error = str(getattr(active_plan, "error", "") or "")

    permission = getattr(snap, "permission_snapshot", None)
    pending = bool(permission and getattr(permission, "has_pending", False))

    agent_pipeline = getattr(snap, "agent_pipeline", None)
    agent_runs = list(getattr(agent_pipeline, "runs", ()) if agent_pipeline else ())
    agent_errors = any(
        str(getattr(r, "state", "")).lower() in {"error", "failed"}
        or str(getattr(r, "error", "") or "")
        for r in agent_runs
    )

    goal_failed = any(
        str(getattr(g, "status", "")).lower() in {"failed", "error"}
        or str(getattr(g, "error", "") or "")
        for g in goals
    )

    if (
        exec_status in {"failed", "error"}
        or exec_error
        or goal_failed
        or agent_errors
        or kernel in {"error", "failed", "crashed"}
    ):
        return MissionMode.FAILURE

    if pending or exec_status in {"awaiting_approval", "paused", "waiting"}:
        return MissionMode.WAITING

    if (
        (active_plan and getattr(active_plan, "is_active", False))
        or exec_status in {"running", "executing"}
        or any(str(getattr(r, "state", "")).lower() in {"running", "active"} for r in agent_runs)
    ):
        return MissionMode.EXECUTING

    if (
        plan_status in {"planning", "planned", "ready"}
        or kernel in {"planning", "reasoning"}
        or any(str(getattr(g, "status", "")).lower() in {"queued", "planning"} for g in goals)
        or str(getattr(agent_pipeline, "pipeline_stage", "") or "").lower()
        in {"planning", "plan", "routing"}
    ):
        return MissionMode.PLANNING

    return MissionMode.IDLE


def mode_label(mode: MissionMode) -> str:
    return {
        MissionMode.IDLE: "Idle",
        MissionMode.PLANNING: "Planning",
        MissionMode.EXECUTING: "Executing",
        MissionMode.WAITING: "Waiting",
        MissionMode.FAILURE: "Failure",
    }[mode]


def mode_color(mode: MissionMode) -> str:
    from ai_command_center.ui.design_system import theme_v2 as T

    return {
        MissionMode.IDLE: T.STATUS_READY,
        MissionMode.PLANNING: T.REASONING_PURPLE,
        MissionMode.EXECUTING: T.EXECUTION_BLUE,
        MissionMode.WAITING: T.STATUS_BUSY,
        MissionMode.FAILURE: T.STATUS_ERROR,
    }[mode]
