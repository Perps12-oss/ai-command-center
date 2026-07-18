"""Approval dashboard — real AppState projection, no placeholder."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.design_system.status_tokens import status_color


class ApprovalsView(ctk.CTkFrame):
    """Displays pending permission checks and resolved approval history."""

    def __init__(
        self,
        master,
        on_command: Callable[[str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_command = on_command
        self._on_navigate = on_navigate
        self._build()

    def _build(self) -> None:
        pending_card = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        pending_card.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        ctk.CTkLabel(
            pending_card,
            text="Pending Approval",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._pending_label = ctk.CTkLabel(
            pending_card,
            text="No pending approvals",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
            justify="left",
        )
        self._pending_label.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        history_card = GlassCard(self, fg_color=T.BG_PANEL, border_color=T.GLASS_BORDER)
        history_card.pack(fill="both", expand=True, padx=T.PAD, pady=(8, T.PAD))

        ctk.CTkLabel(
            history_card,
            text="Approval History",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))

        self._history_list = ctk.CTkFrame(history_card, fg_color="transparent")
        self._history_list.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        self._history_rows: list[ctk.CTkLabel] = []
        for _ in range(10):
            lbl = ctk.CTkLabel(
                self._history_list,
                text="",
                font=T.FONT_BODY,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                justify="left",
            )
            lbl.pack(fill="x", pady=(0, 2))
            self._history_rows.append(lbl)

    def apply_state(self, snap: Any) -> None:
        """Project pending and resolved permission checks into the view."""
        permission = getattr(snap, "permission_snapshot", None)
        pending = getattr(permission, "pending", None) if permission else None

        if pending:
            perms = ", ".join(getattr(pending, "permissions", ()))
            self._pending_label.configure(
                text=(
                    f"{getattr(pending, 'actor_type', 'agent')} "
                    f"{getattr(pending, 'actor_id', '')} requests: {perms}\n"
                    f"{getattr(pending, 'summary', '')}"
                ),
                text_color=T.TEXT_PRIMARY,
            )
        else:
            self._pending_label.configure(text="No pending approvals", text_color=T.TEXT_SECONDARY)

        resolved = list(getattr(permission, "resolved", ()) if permission else ())
        for i, lbl in enumerate(self._history_rows):
            if i < len(resolved):
                check = resolved[i]
                granted = getattr(check, "granted", False)
                verdict = "granted" if granted else "denied"
                fg = status_color("ready") if granted else status_color("error")
                summary = getattr(check, "summary", "")
                actor = getattr(check, "actor_id", "")
                lbl.configure(text=f"{actor}: {verdict} — {summary}", text_color=fg)
            else:
                lbl.configure(text="", text_color=T.TEXT_SECONDARY)
