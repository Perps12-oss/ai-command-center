"""ChatHeader — title, metadata, search, and actions."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_STATUS_COLORS: dict[str, str] = {
    "idle": T.TEXT_MUTED,
    "streaming": T.STATUS_BUSY,
    "ready": T.STATUS_READY,
    "error": T.STATUS_ERROR,
    "cancelled": T.TEXT_MUTED,
}


class ChatHeader(ctk.CTkFrame):
    """Horizontal header bar for the chat center pane."""

    def __init__(
        self,
        master: Any,
        *,
        on_rename: Callable[[str], None] | None = None,
        on_export: Callable[[], None] | None = None,
        on_pin: Callable[[], None] | None = None,
        on_archive: Callable[[], None] | None = None,
        on_share: Callable[[], None] | None = None,
        on_search: Callable[[], None] | None = None,
        on_toggle_history: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.SURFACE_PRIMARY,
            corner_radius=0,
            height=56,
            border_width=0,
            **kwargs,
        )
        self.pack_propagate(False)

        self._on_rename = on_rename
        self._on_export = on_export
        self._on_pin = on_pin
        self._on_archive = on_archive
        self._on_share = on_share
        self._on_search = on_search
        self._on_toggle_history = on_toggle_history

        self._title_text = "New Chat"
        self._model = ""
        self._message_count = 0
        self._pinned = False
        self._more_menu: ctk.CTkToplevel | None = None

        self._build()

    def _build(self) -> None:
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=8)

        self._title_lbl = ctk.CTkLabel(
            left,
            text=self._title_text,
            font=(T.FONT_FAMILY, 14, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title_lbl.pack(fill="x", anchor="w")
        self._title_lbl.bind("<Double-Button-1>", self._start_rename)

        self._meta_lbl = ctk.CTkLabel(
            left,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._meta_lbl.pack(fill="x", anchor="w", pady=(2, 0))

        self._status_lbl = ctk.CTkLabel(
            left,
            text="",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        )

        self._build_actions()

    def _build_actions(self) -> None:
        btn_cfg: dict[str, Any] = dict(
            width=30,
            height=30,
            font=(T.FONT_FAMILY, 13),
            fg_color="transparent",
            hover_color=T.SURFACE_ELEVATED,
            text_color=T.TEXT_MUTED,
            corner_radius=T.BUTTON_RADIUS,
        )

        ctk.CTkButton(
            self, text="⋯", command=self._show_more_menu, **btn_cfg
        ).pack(side="right", padx=(4, 12), pady=12)

        if self._on_share:
            ctk.CTkButton(
                self, text="↗", command=self._on_share, **btn_cfg
            ).pack(side="right", padx=2, pady=12)

        if self._on_pin:
            self._fav_btn = ctk.CTkButton(
                self, text="☆", command=self._on_pin, **btn_cfg
            )
            self._fav_btn.pack(side="right", padx=2, pady=12)

        if self._on_search:
            ctk.CTkButton(
                self, text="🔍", command=self._on_search, **btn_cfg
            ).pack(side="right", padx=2, pady=12)

    def _show_more_menu(self) -> None:
        if self._more_menu and self._more_menu.winfo_exists():
            self._more_menu.destroy()
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.configure(fg_color=T.SURFACE_ELEVATED)
        x = self.winfo_rootx() + self.winfo_width() - 160
        y = self.winfo_rooty() + self.winfo_height()
        menu.geometry(f"150x120+{x}+{y}")

        items: list[tuple[str, Callable[[], None] | None]] = [
            ("Rename", lambda: self._start_rename()),
            ("Archive", self._on_archive),
            ("Export", self._on_export),
        ]
        for label, cmd in items:
            if cmd:
                ctk.CTkButton(
                    menu,
                    text=label,
                    anchor="w",
                    height=32,
                    font=T.FONT_SMALL,
                    fg_color="transparent",
                    hover_color=T.SURFACE_SECONDARY,
                    text_color=T.TEXT_PRIMARY,
                    command=lambda c=cmd, m=menu: (m.destroy(), c()),
                ).pack(fill="x", padx=4, pady=2)
        self._more_menu = menu
        menu.bind("<FocusOut>", lambda _: menu.destroy() if menu.winfo_exists() else None)
        menu.focus_set()

    def update_title(self, title: str) -> None:
        self._title_text = title or "New Chat"
        self._title_lbl.configure(text=self._title_text)
        self._refresh_meta()

    def update_metadata(self, *, model: str, message_count: int) -> None:
        self._model = model
        self._message_count = message_count
        self._refresh_meta()

    def update_model(self, model: str) -> None:
        self._model = model
        self._refresh_meta()

    def _refresh_meta(self) -> None:
        parts: list[str] = []
        if self._model:
            parts.append(self._model)
        if self._message_count:
            n = self._message_count
            parts.append(f"{n} message{'s' if n != 1 else ''}")
        parts.append("Today")
        self._meta_lbl.configure(text=" · ".join(parts))

    def update_provider(self, provider: str, model: str) -> None:
        del provider
        self._model = model
        self._refresh_meta()

    def update_status(self, status: str) -> None:
        color = _STATUS_COLORS.get(status, T.TEXT_MUTED)
        icons = {
            "streaming": "● streaming",
            "error": "✕ error",
            "ready": "",
            "idle": "",
            "cancelled": "✕ cancelled",
        }
        text = icons.get(status, "")
        if text:
            self._status_lbl.configure(text=text, text_color=color)
            if not self._status_lbl.winfo_ismapped():
                self._status_lbl.pack(fill="x", anchor="w", pady=(2, 0))
        elif self._status_lbl.winfo_ismapped():
            self._status_lbl.pack_forget()

    def set_pinned(self, pinned: bool) -> None:
        self._pinned = pinned
        if hasattr(self, "_fav_btn"):
            self._fav_btn.configure(
                text="★" if pinned else "☆",
                text_color=T.ACCENT_PURPLE if pinned else T.TEXT_MUTED,
            )

    def _start_rename(self, _: Any = None) -> None:
        if not self._on_rename:
            return
        self._title_lbl.pack_forget()
        self._entry_var = ctk.StringVar(value=self._title_text)
        self._rename_entry = ctk.CTkEntry(
            self,
            textvariable=self._entry_var,
            font=(T.FONT_FAMILY, 14, "bold"),
            fg_color=T.SURFACE_ELEVATED,
            border_color=T.BORDER_SUBTLE,
            text_color=T.TEXT_PRIMARY,
            width=280,
        )
        self._rename_entry.pack(side="left", padx=(16, 0), pady=12)
        self._rename_entry.focus_set()
        self._rename_entry.bind("<Return>", self._commit_rename)
        self._rename_entry.bind("<Escape>", self._cancel_rename)

    def _commit_rename(self, _: Any = None) -> None:
        new_title = self._entry_var.get().strip()
        if new_title and self._on_rename:
            self._on_rename(new_title)
        self._cancel_rename()

    def _cancel_rename(self, _: Any = None) -> None:
        if hasattr(self, "_rename_entry"):
            self._rename_entry.destroy()
        self._title_lbl.pack(fill="x", anchor="w")
