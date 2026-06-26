"""Semantic color helpers for the Workspace Design System."""

from __future__ import annotations

from ai_command_center.ui.design_system.theme_v2 import (
    STATUS_BUSY,
    STATUS_ERROR,
    STATUS_READY,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def status_color(state: str) -> str:
    """Map a service state string to a semantic colour."""
    s = str(state).lower()
    if s in {"ready", "online", "active", "idle", "ok"}:
        return STATUS_READY
    if s in {"busy", "starting", "loading", "indexing", "degraded"}:
        return STATUS_BUSY
    if s in {"error", "offline", "stopped", "failed"}:
        return STATUS_ERROR
    return TEXT_MUTED


def text_color(role: str) -> str:
    """Map a text role to a colour token."""
    r = str(role).lower()
    if r == "primary":
        return TEXT_PRIMARY
    if r == "secondary":
        return TEXT_SECONDARY
    return TEXT_MUTED
