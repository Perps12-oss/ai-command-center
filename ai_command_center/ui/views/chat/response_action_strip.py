"""ResponseActionStrip — Open WebUI–style action bar below assistant messages.

Shows: Execution #N | N Artifacts | N Decisions
Tapping any pill opens the inspector via InspectableRef selection.

Architecture contract: pure display widget, no bus/service imports.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.design_system import theme_v2 as T


def _execution_ref(execution_id: str, execution_index: int) -> InspectableRef:
    ref_id = execution_id or (f"exec-{execution_index}" if execution_index else "execution-stub")
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


def _artifact_ref(execution_id: str, count: int) -> InspectableRef:
    ref_id = f"{execution_id}-artifacts" if execution_id else "artifacts-stub"
    return InspectableRef.from_payload(
        {
            "kind": "artifact",
            "ref_id": ref_id,
            "label": f"{count} Artifacts" if count else "Artifacts",
            "payload": {
                "artifact_count": str(count),
                "execution_id": execution_id,
            },
        }
    )


def _decision_ref(execution_id: str, count: int) -> InspectableRef:
    ref_id = f"{execution_id}-decisions" if execution_id else "decisions-stub"
    return InspectableRef.from_payload(
        {
            "kind": "decision",
            "ref_id": ref_id,
            "label": f"{count} Decisions" if count else "Decisions",
            "payload": {
                "decision_count": str(count),
                "execution_id": execution_id,
            },
        }
    )


class _ActionPill(ctk.CTkButton):
    """Small pill button for the action strip."""

    def __init__(
        self,
        master: Any,
        text: str,
        inspect_ref: InspectableRef,
        on_select: Callable[[InspectableRef], None] | None,
        on_navigate: Callable[[InspectableRef], None] | None = None,
        count: int = 0,
    ) -> None:
        label = f"{text}  {count}" if count else text
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
            command=lambda: on_select(inspect_ref) if on_select else None,
        )
        self._inspect_ref = inspect_ref
        if on_navigate is not None:
            self.bind(
                "<Double-Button-1>",
                lambda _e: on_navigate(inspect_ref),
                add="+",
            )


class ResponseActionStrip(ctk.CTkFrame):
    """Horizontal strip of action pills below an assistant message.

    ┌────────────────────────────────────────────────────────┐
    │  ⚡ Execution #3  │  📄 2 Artifacts  │  ✓ 1 Decision  │
    └────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        *,
        execution_id: str = "",
        execution_index: int = 0,
        artifact_count: int = 0,
        decision_count: int = 0,
        on_inspect_select: Callable[[InspectableRef], None] | None = None,
        on_inspect_navigate: Callable[[InspectableRef], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_inspect_select = on_inspect_select
        self._on_inspect_navigate = on_inspect_navigate

        if execution_id or execution_index:
            label = f"⚡ Execution #{execution_index}" if execution_index else "⚡ Execution"
            _ActionPill(
                self,
                label,
                _execution_ref(execution_id, execution_index),
                on_inspect_select,
                on_inspect_navigate,
            ).pack(side="left", padx=(0, 4))

        if artifact_count:
            _ActionPill(
                self,
                "📄 Artifacts",
                _artifact_ref(execution_id, artifact_count),
                on_inspect_select,
                on_inspect_navigate,
                count=artifact_count,
            ).pack(side="left", padx=(0, 4))

        if decision_count:
            _ActionPill(
                self,
                "✓ Decisions",
                _decision_ref(execution_id, decision_count),
                on_inspect_select,
                on_inspect_navigate,
                count=decision_count,
            ).pack(side="left", padx=(0, 4))
