"""Approval Center workspace — Article 15 operational surface (Phase 11E).

Architecture contract:
- Pure renderer. Reads AppState via apply_state(snapshot) only.
- Uses AppState.permission_snapshot exclusively (+ optional execution risk compose).
- Approve/Deny publish PERMISSION_CHECK_RESULT through callbacks.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.permission_check_snapshot import (
    PendingCheck,
    PermissionCheckSnapshot,
)
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.approval_center import (
    ApprovalStatisticsPanel,
    DecisionHistoryPanel,
    PendingQueuePanel,
    RiskClassificationPanel,
)


class ApprovalsView(ctk.CTkFrame):
    """Approval Center orchestration shell (Hero + four Article 15 panels)."""

    def __init__(
        self,
        master: Any,
        *,
        on_decide: Callable[[str, bool, tuple[str, ...], str, str], None] | None = None,
        on_select: Callable[[str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        on_command: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_decide = on_decide
        self._on_select = on_select or (lambda _cid: None)
        self._on_navigate = on_navigate
        self._on_command = on_command
        self._focused_check_id = ""
        self._last_snap: AppState | None = None
        self._build()

    def _build(self) -> None:
        self._hero = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.APPROVAL_ORANGE)
        self._hero.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD, pady=(T.PAD, 0))
        ctk.CTkLabel(
            top,
            text="Approval Center",
            font=T.FONT_TITLE,
            text_color=T.APPROVAL_ORANGE,
            anchor="w",
        ).pack(side="left")
        self._metrics = ctk.CTkLabel(
            top,
            text="0 pending · 0 granted · 0 denied · No decisions recorded",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="e",
        )
        self._metrics.pack(side="right")

        bottom = ctk.CTkFrame(self._hero, fg_color="transparent")
        bottom.pack(fill="x", padx=T.PAD, pady=(8, T.PAD))
        self._hero_hint = ctk.CTkLabel(
            bottom,
            text=(
                "No pending approvals. Interactive checks appear when supervised "
                "authorization is requested."
            ),
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._hero_hint.pack(side="left", fill="x", expand=True)
        self._hero_action = ctk.CTkButton(
            bottom,
            text="Review Next",
            font=T.FONT_BODY,
            fg_color=T.APPROVAL_ORANGE,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_PRIMARY,
            height=28,
            width=140,
            state="disabled",
            command=self._review_next,
        )
        self._hero_action.pack(side="right", padx=(8, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        # Pending Queue dominates (Correction #3).
        body.grid_rowconfigure(0, weight=3)
        body.grid_rowconfigure(1, weight=2)

        self._queue = PendingQueuePanel(
            body,
            on_approve=lambda p: self._decide(p, True),
            on_deny=lambda p: self._decide(p, False),
            on_select=self._focus,
        )
        self._queue.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._risk = RiskClassificationPanel(right)
        self._risk.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self._history = DecisionHistoryPanel(right)
        self._history.grid(row=1, column=0, sticky="nsew")

        self._stats = ApprovalStatisticsPanel(body)
        self._stats.grid(row=1, column=0, columnspan=2, sticky="nsew")

    def apply_state(self, snapshot: AppState | Any) -> None:
        """Project AppState.permission_snapshot into Hero + panels."""
        if not isinstance(snapshot, AppState):
            return
        self._last_snap = snapshot
        permission = snapshot.permission_snapshot
        pending_n = 1 if permission.has_pending else 0
        last = self._last_decision_label(permission)
        self._metrics.configure(
            text=(
                f"{pending_n} pending · {permission.total_granted} granted · "
                f"{permission.total_denied} denied · {last}"
            )
        )
        if permission.has_pending and permission.pending is not None:
            self._hero_hint.configure(
                text=f"Pending: {permission.pending.summary or permission.pending.check_id}"
            )
            self._hero_action.configure(state="normal")
            if not self._focused_check_id:
                self._focused_check_id = permission.pending.check_id
        else:
            self._hero_hint.configure(
                text=(
                    "No pending approvals. Interactive checks appear when supervised "
                    "authorization is requested."
                )
            )
            self._hero_action.configure(state="disabled")
            self._focused_check_id = ""

        library = snapshot.execution_library
        self._queue.apply_snapshot(
            permission,
            execution_library=library,
            focused_check_id=self._focused_check_id,
        )
        self._risk.apply_snapshot(permission, execution_library=library)
        self._history.apply_snapshot(permission)
        self._stats.apply_snapshot(permission)

    @staticmethod
    def _last_decision_label(permission: PermissionCheckSnapshot) -> str:
        """Correction #1: last decision from resolved ordering only."""
        latest = permission.last_resolved
        if latest is None:
            return "No decisions recorded"
        outcome = "granted" if latest.granted else "denied"
        return f"Last: {outcome}"

    def _review_next(self) -> None:
        if self._last_snap is None:
            return
        pending = self._last_snap.permission_snapshot.pending
        if pending is None:
            return
        self._focus(pending.check_id)

    def _focus(self, check_id: str) -> None:
        self._focused_check_id = str(check_id)
        self._on_select(self._focused_check_id)
        if self._last_snap is not None:
            self.apply_state(self._last_snap)

    def _decide(self, pending: PendingCheck, granted: bool) -> None:
        if self._on_decide is None:
            return
        self._on_decide(
            pending.check_id,
            granted,
            tuple(pending.permissions),
            pending.actor_type,
            pending.actor_id,
        )
