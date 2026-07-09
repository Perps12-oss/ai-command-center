"""ExecutionBadge — compact execution indicator that opens the inspector.

Clicking the badge publishes an InspectableRef for the execution scope.
Architecture contract: pure display widget, no bus/service imports.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.design_system import theme_v2 as T


def execution_inspect_ref(execution_id: str, execution_index: int = 0) -> InspectableRef | None:
    if not execution_id and not execution_index:
        return None
    ref_id = execution_id or f"exec-{execution_index}"
    label = f"Execution #{execution_index}" if execution_index else "Execution"
    return InspectableRef.from_payload(
        {
            "kind": "execution",
            "ref_id": ref_id,
            "label": label,
            "payload": {
                "execution_id": execution_id,
                "index": str(execution_index),
            },
        }
    )


class ExecutionBadge(ctk.CTkButton):
    """Small clickable badge: ⚡ Execution #N → Inspector."""

    def __init__(
        self,
        master: Any,
        *,
        execution_id: str = "",
        execution_index: int = 0,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_inspect_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        label = f"⚡ Execution #{execution_index}" if execution_index else "⚡ Execution"
        super().__init__(
            master,
            text=label,
            height=22,
            font=(T.FONT_FAMILY, 10),
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
            command=self._on_click,
            **kwargs,
        )
        self._inspect_ref = execution_inspect_ref(execution_id, execution_index)
        self._on_inspect_select = on_inspect_select
        self._on_inspect_navigate = on_inspect_navigate
        if self._inspect_ref is None:
            self.configure(state="disabled")
        elif on_inspect_navigate is not None:
            self.bind(
                "<Double-Button-1>",
                lambda _e: on_inspect_navigate(self._inspect_ref),
                add="+",
            )

    def _on_click(self) -> None:
        if self._inspect_ref is None:
            return
        if self._on_inspect_select is not None:
            self._on_inspect_select(self._inspect_ref)

    @property
    def inspect_ref(self) -> InspectableRef | None:
        return self._inspect_ref


__all__ = ["ExecutionBadge", "execution_inspect_ref"]
