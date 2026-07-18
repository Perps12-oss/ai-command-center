"""Semantic color helpers for the Workspace Design System."""

from __future__ import annotations

from ai_command_center.ui.design_system.theme_v2 import (
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ai_command_center.ui.design_system.status_tokens import status_color

__all__ = ["status_color", "text_color"]


def text_color(role: str) -> str:
    """Map a text role to a colour token."""
    r = str(role).lower()
    if r == "primary":
        return TEXT_PRIMARY
    if r == "secondary":
        return TEXT_SECONDARY
    return TEXT_MUTED
