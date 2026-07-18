"""Shared Loading / Empty / Error / Data banner helpers for Phase 11 shells.

Article 18 — empty states must explain why nothing is shown, what creates
data, and what action the user can take next. Never bare "No Data".
"""

from __future__ import annotations

from typing import Any

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color

LOADING_TEXT = "Loading…"


def article18_empty(*, why: str, creates: str, next_action: str) -> str:
    """Format a three-part Article 18 empty-state message."""
    return f"{why}\n{creates}\nNext: {next_action}"


def article18_loading(*, status: str, what: str, next_action: str) -> str:
    """Format a three-part loading banner (status / what / next action)."""
    return f"{status}\nLoading: {what}\nNext: {next_action}"


def domain_error_from_snap(
    snap: Any,
    *,
    topic_prefixes: tuple[str, ...] = (),
    error_attr: str = "",
) -> str:
    """Return an error message when last_event or a domain field indicates failure."""
    if snap is None:
        return ""
    topic = str(getattr(snap, "last_event_topic", "") or "").lower()
    errors = getattr(snap, "errors", ()) or ()
    if topic_prefixes and any(topic.startswith(p) for p in topic_prefixes) and (
        "error" in topic or topic.endswith(".failed")
    ):
        if errors:
            return str(errors[-1])
        return f"Last event reported an error ({topic})."
    if "error" in topic or topic.endswith(".failed"):
        # Global error event — only surface when domain prefixes match or none given.
        if not topic_prefixes or any(topic.startswith(p) for p in topic_prefixes):
            if errors:
                return str(errors[-1])
            return f"Last event reported an error ({topic})."
    if error_attr:
        value = getattr(snap, error_attr, None)
        if value:
            return str(value)
        # Nested domain snapshots (e.g. execution_library.active_plan.error)
        parts = error_attr.split(".")
        cur: Any = snap
        for part in parts:
            cur = getattr(cur, part, None) if cur is not None else None
        if cur:
            return str(cur)
    if errors and not topic_prefixes:
        return str(errors[-1])
    return ""


def set_surface_state(
    label: Any,
    *,
    kind: str,
    message: str = "",
) -> None:
    """Update a `_surface_state` banner label.

    kind: ``loading`` | ``empty`` | ``error`` | ``data``
    When ``data``, the banner is cleared (hidden visually via empty text).
    """
    kind = (kind or "data").lower().strip()
    if kind == "loading":
        label.configure(
            text=message
            or article18_loading(
                status="Status: loading workspace projection",
                what="AppState snapshot for this surface",
                next_action="Wait for the next state refresh; no action required.",
            ),
            text_color=T.TEXT_MUTED,
        )
    elif kind == "error":
        label.configure(
            text=message or "An error occurred.",
            text_color=status_color("error"),
        )
    elif kind == "empty":
        label.configure(
            text=message or article18_empty(
                why="Nothing is available to display yet.",
                creates="Data appears when the related workspace activity runs.",
                next_action="Use the primary action in this workspace.",
            ),
            text_color=T.TEXT_MUTED,
        )
    else:
        label.configure(text="", text_color=T.TEXT_MUTED)
