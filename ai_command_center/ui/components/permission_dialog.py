"""Interactive permission approval dialog for supervised agent actions."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class PermissionDialog(ctk.CTkToplevel):
    """Modal approve/deny dialog for permission.check.request (Track 7 A2)."""

    def __init__(
        self,
        master,
        *,
        check_id: str,
        permissions: list[str],
        actor_type: str,
        actor_id: str,
        summary: str,
        on_result: Callable[[bool], None],
    ) -> None:
        super().__init__(master)
        self._check_id = check_id
        self._on_result = on_result
        self._answered = False

        self.title("Permission required")
        self.configure(fg_color=T.BG_PANEL)
        self.geometry("460x240")
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._deny)

        ctk.CTkLabel(
            self,
            text="Supervised action needs approval",
            font=(T.FONT_FAMILY, 14, "bold"),
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            self,
            text=summary,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            wraplength=420,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 8))

        perm_text = ", ".join(permissions) if permissions else "—"
        ctk.CTkLabel(
            self,
            text=f"Permissions: {perm_text}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            wraplength=420,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 4))

        actor_label = actor_id[:12] + "…" if len(actor_id) > 12 else actor_id
        ctk.CTkLabel(
            self,
            text=f"Actor: {actor_type} ({actor_label or 'unknown'})",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 12))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(0, 16))

        ctk.CTkButton(
            btn_row,
            text="Deny",
            width=100,
            fg_color=T.BG_GLASS,
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.STATUS_ERROR,
            command=self._deny,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row,
            text="Approve",
            width=100,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            command=self._approve,
        ).pack(side="right")

    def _finish(self, granted: bool) -> None:
        if self._answered:
            return
        self._answered = True
        try:
            self._on_result(granted)
        finally:
            self.destroy()

    def _approve(self) -> None:
        self._finish(True)

    def _deny(self) -> None:
        self._finish(False)
