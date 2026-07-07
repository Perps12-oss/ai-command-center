"""Canonical inspect gestures: single-click select, double-click navigate."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any

from ai_command_center.domain.inspectable import InspectableRef

logger = logging.getLogger(__name__)


def bind_inspect_gestures(
    widgets: Iterable[Any],
    *,
    get_ref: Callable[[], InspectableRef | None],
    on_select: Callable[[InspectableRef], None] | None,
    on_navigate: Callable[[InspectableRef], None] | None,
) -> None:
    if on_select is None and on_navigate is None:
        return

    def _handle_select(_event: Any) -> None:
        ref = get_ref()
        if ref is not None and on_select is not None:
            on_select(ref)

    def _handle_navigate(_event: Any) -> None:
        ref = get_ref()
        if ref is not None and on_navigate is not None:
            on_navigate(ref)

    for widget in widgets:
        try:
            widget.bind("<Button-1>", _handle_select, add="+")
            widget.bind("<Double-Button-1>", _handle_navigate, add="+")
        except Exception:
            logger.warning(
                "Failed to bind inspect gestures on %r",
                widget,
                exc_info=True,
            )


__all__ = ["bind_inspect_gestures"]
