"""Status tokens — single source of truth for UI status colors."""

from __future__ import annotations

from ai_command_center.ui.design_system import theme_v2 as T

# (foreground, background)
_READY = (T.STATUS_READY, T.STATUS_READY_BG)
_BUSY = (T.STATUS_BUSY, T.STATUS_BUSY_BG)
_ERROR = (T.STATUS_ERROR, T.STATUS_ERROR_BG)
_OFFLINE = (T.TEXT_MUTED, T.STATUS_OFFLINE_BG)


def _canonical_status(state: str) -> tuple[str, str]:
    """Map arbitrary status strings to a canonical (foreground, background) pair."""
    s = str(state).lower().strip()
    if s in {"ready", "complete", "completed", "success", "passed", "healthy", "ok"}:
        return _READY
    if s in {
        "running",
        "busy",
        "waiting",
        "blocked",
        "paused",
        "starting",
        "boot",
        "booting",
        "degraded",
        "active",
        "queued",
        "awaiting_approval",
        "pending",
        "in_progress",
    }:
        return _BUSY
    if s in {"error", "failed", "failure", "denied", "rejected", "stopped", "abandoned", "cancelled"}:
        return _ERROR
    if s in {"offline", "none", "no", "offline"}:
        return _OFFLINE
    return _READY


def status_color(state: str) -> str:
    """Foreground color for a generic status string."""
    return _canonical_status(state)[0]


def status_badge(state: str) -> tuple[str, str]:
    """(foreground, background) for a generic status badge."""
    return _canonical_status(state)


def kernel_state_color(state: str) -> tuple[str, str]:
    """(foreground, background) for a kernel state."""
    s = str(state).lower().strip()
    if s in {"ready", "complete"}:
        return _READY
    if s in {"boot", "booting", "starting", "busy", "running"}:
        return _BUSY
    if s in {"error", "failed", "stopped"}:
        return _ERROR
    if s in {"offline"}:
        return _OFFLINE
    return _READY


def goal_state_color(state: str) -> tuple[str, str]:
    """(foreground, background) for a goal state."""
    s = str(state).lower().strip()
    if s in {"active", "running", "queued", "in_progress"}:
        return _BUSY
    if s in {"paused", "blocked", "waiting"}:
        return _BUSY
    if s in {"complete", "completed", "ready", "done", "success"}:
        return _READY
    if s in {"failed", "error", "cancelled", "abandoned", "denied"}:
        return _ERROR
    if s in {"offline"}:
        return _OFFLINE
    return _READY


def execution_state_color(state: str) -> tuple[str, str]:
    """(foreground, background) for an execution state."""
    s = str(state).lower().strip()
    if s in {"running", "awaiting_approval", "busy", "starting", "queued", "in_progress"}:
        return _BUSY
    if s in {"complete", "completed", "ready", "done", "success"}:
        return _READY
    if s in {"failed", "error", "stopped", "cancelled"}:
        return _ERROR
    if s in {"offline"}:
        return _OFFLINE
    return _READY
