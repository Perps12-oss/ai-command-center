"""Spacing helpers for the Workspace Design System."""

from __future__ import annotations

from ai_command_center.ui.design_system.theme_v2 import CORNER_RADIUS, GAP, PAD


__all__ = ["pad", "gap", "radius", "inset"]


def pad(multiplier: int = 1) -> int:
    return PAD * multiplier


def gap(multiplier: int = 1) -> int:
    return GAP * multiplier


def radius() -> int:
    return CORNER_RADIUS


def inset(horizontal: int = 1, vertical: int = 1) -> dict[str, tuple[int, int]]:
    return {
        "padx": (PAD * horizontal, PAD * horizontal),
        "pady": (PAD * vertical, PAD * vertical),
    }
