"""Typography helpers for the Workspace Design System."""

from __future__ import annotations

from ai_command_center.ui.design_system.theme_v2 import (
    FONT_BODY,
    FONT_FAMILY,
    FONT_HEADER,
    FONT_MONO,
    FONT_ROLE,
    FONT_SMALL,
    FONT_TITLE,
)


def title() -> tuple:
    return FONT_TITLE


def header() -> tuple:
    return FONT_HEADER


def body() -> tuple:
    return FONT_BODY


def small() -> tuple:
    return FONT_SMALL


def mono() -> tuple:
    return FONT_MONO


def role_label() -> tuple:
    return FONT_ROLE


def custom(size: int, weight: str = "normal") -> tuple:
    return (FONT_FAMILY, size, weight)
