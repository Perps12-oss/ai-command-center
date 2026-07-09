"""Specialized workflow node overlays (Slice 1b)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.domain.workflow_graph import GraphNode, NodeState
from ai_command_center.ui.design_system import theme_v2 as T


class ApprovalNodeBadge(ctk.CTkFrame):
    """Compact approval-gate indicator for workflow graphs."""

    def __init__(self, master: Any, *, label: str = "Approval", **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=T.STATUS_BUSY_BG,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=T.ACCENT_DEFAULT,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text=f"✓ {label}",
            font=(T.FONT_FAMILY, 9, "bold"),
            text_color=T.ACCENT_DEFAULT,
        ).pack(padx=8, pady=4)


class RetryVisualization(ctk.CTkFrame):
    """Retry loop indicator for failed/running retry nodes."""

    def __init__(
        self,
        master: Any,
        *,
        attempt: int = 1,
        max_attempts: int = 3,
        state: NodeState = NodeState.PENDING,
        **kwargs: Any,
    ) -> None:
        color = T.STATUS_ERROR if state == NodeState.FAILED else T.STATUS_BUSY
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=color,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text=f"↻ Retry {attempt}/{max_attempts}",
            font=(T.FONT_FAMILY, 9),
            text_color=color,
        ).pack(padx=8, pady=4)


def node_overlay_kind(node: GraphNode) -> str | None:
    """Return overlay kind for specialized node rendering."""
    kind = str(node.kind or "").lower()
    if kind in {"approval", "approve", "gate"}:
        return "approval"
    if kind in {"retry", "retry_loop"}:
        return "retry"
    if node.state == NodeState.WAITING:
        return "approval"
    return None


__all__ = ["ApprovalNodeBadge", "RetryVisualization", "node_overlay_kind"]
