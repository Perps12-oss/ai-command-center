"""ChatHeader — conversation name + provider pill + execution status bar.

Replaces the legacy _SessionBar in chat_view.py.

Data contract (read-only from AppState via public update methods):
  - conversation title / rename
  - provider name + model
  - execution status (idle / streaming / error)
  - provider health indicator
  - Rename / Export / Pin / Archive action buttons

Architecture contract
─────────────────────
• No EventBus, service, or repository imports.
• All actions call back via on_rename / on_export / on_pin / on_archive.
• Data flows in via update_*() methods called from the UIQueue.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_STATUS_COLORS: dict[str, str] = {
    "idle":      T.TEXT_MUTED,
    "streaming": T.STATUS_BUSY,
    "ready":     T.STATUS_READY,
    "error":     T.STATUS_ERROR,
    "cancelled": T.TEXT_MUTED,
}

_PROVIDER_COLORS: dict[str, str] = {
    "ollama":  "#22C55E",
    "openai":  "#3B82F6",
    "local":   "#A78BFA",
    "default": T.TEXT_MUTED,
}


class ChatHeader(ctk.CTkFrame):
    """Horizontal header bar for the chat center pane.

    ┌─────────────────────────────────────────────────────────────┐
    │  ◈  Conversation title          [ollama]  [●streaming]  ···  │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        *,
        on_rename: Callable[[str], None]  | None = None,
        on_export: Callable[[], None]     | None = None,
        on_pin:    Callable[[], None]     | None = None,
        on_archive: Callable[[], None]    | None = None,
        on_toggle_history: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            corner_radius=0,
            height=44,
            **kwargs,
        )
        self.pack_propagate(False)

        self._on_rename = on_rename
        self._on_export = on_export
        self._on_pin = on_pin
        self._on_archive = on_archive
        self._on_toggle_history = on_toggle_history

        self._title_text = "New Chat"
        self._provider = ""
        self._model = ""
        self._status = "idle"
        self._pinned = False

        self._build()

    def _build(self) -> None:
        # History toggle button (left edge)
        if self._on_toggle_history:
            self._toggle_btn = ctk.CTkButton(
                self,
                text="◧",
                width=28, height=28,
                font=(T.FONT_FAMILY, 13),
                fg_color="transparent",
                hover_color=T.BG_GLASS,
                text_color=T.TEXT_MUTED,
                corner_radius=T.SMALL_RADIUS,
                command=self._on_toggle_history,
            )
            self._toggle_btn.pack(side="left", padx=(8, 4), pady=8)

        # Title label (editable on double-click)
        self._title_lbl = ctk.CTkLabel(
            self,
            text=self._title_text,
            font=(T.FONT_FAMILY, 12, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        self._title_lbl.pack(side="left", padx=(6, 0), pady=10)
        self._title_lbl.bind("<Double-Button-1>", self._start_rename)

        # Separator
        ctk.CTkFrame(self, width=1, height=20, fg_color=T.BG_GLASS_BORDER).pack(
            side="left", padx=8, pady=12
        )

        # Provider badge pill
        self._provider_badge = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            width=60,
        )
        self._provider_badge.pack(side="left", padx=(0, 6), pady=10)

        # Status indicator
        self._status_lbl = ctk.CTkLabel(
            self,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._status_lbl.pack(side="left", padx=(0, 4), pady=10)

        # Right-side action buttons
        self._build_actions()

    def _build_actions(self) -> None:
        """Build the right-edge action buttons."""
        btn_cfg: dict[str, Any] = dict(
            width=26, height=26,
            font=(T.FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=T.BG_GLASS,
            text_color=T.TEXT_MUTED,
            corner_radius=T.SMALL_RADIUS,
        )

        if self._on_archive:
            ctk.CTkButton(
                self, text="▾", command=self._on_archive, **btn_cfg
            ).pack(side="right", padx=4, pady=9)

        if self._on_pin:
            self._pin_btn = ctk.CTkButton(
                self, text="📌", command=self._on_pin, **btn_cfg
            )
            self._pin_btn.pack(side="right", padx=2, pady=9)

        if self._on_export:
            ctk.CTkButton(
                self, text="⬇", command=self._on_export, **btn_cfg
            ).pack(side="right", padx=2, pady=9)

        # Vertical divider before right buttons
        ctk.CTkFrame(self, width=1, height=20, fg_color=T.BG_GLASS_BORDER).pack(
            side="right", padx=4, pady=12
        )

    # ── public update API ─────────────────────────────────────────────

    def update_title(self, title: str) -> None:
        """Set the conversation title."""
        self._title_text = title or "New Chat"
        self._title_lbl.configure(text=self._title_text)

    def update_provider(self, provider: str, model: str) -> None:
        """Set provider name and model."""
        self._provider = provider
        self._model = model
        color = _PROVIDER_COLORS.get(provider.lower(), _PROVIDER_COLORS["default"])
        badge_text = provider.upper()[:8] if provider else "—"
        self._provider_badge.configure(text=badge_text, text_color=color)

    def update_status(self, status: str) -> None:
        """Update execution status: idle | streaming | ready | error."""
        self._status = status
        color = _STATUS_COLORS.get(status, T.TEXT_MUTED)
        icons = {
            "streaming": "● streaming",
            "error":     "✕ error",
            "ready":     "✓ ready",
            "idle":      "",
            "cancelled": "✕ cancelled",
        }
        self._status_lbl.configure(
            text=icons.get(status, ""),
            text_color=color,
        )

    def update_model(self, model: str) -> None:
        self._model = model

    def set_pinned(self, pinned: bool) -> None:
        self._pinned = pinned
        if hasattr(self, "_pin_btn"):
            self._pin_btn.configure(
                text_color=T.ACCENT_DEFAULT if pinned else T.TEXT_MUTED
            )

    # ── rename inline edit ────────────────────────────────────────────

    def _start_rename(self, _: Any = None) -> None:
        if not self._on_rename:
            return
        self._title_lbl.pack_forget()
        self._entry_var = ctk.StringVar(value=self._title_text)
        self._rename_entry = ctk.CTkEntry(
            self,
            textvariable=self._entry_var,
            width=200, height=26,
            font=(T.FONT_FAMILY, 12),
            fg_color=T.BG_INPUT,
            border_color=T.ACCENT_DEFAULT,
            text_color=T.TEXT_PRIMARY,
        )
        self._rename_entry.pack(side="left", padx=(0, 6), pady=9)
        self._rename_entry.focus_set()
        self._rename_entry.bind("<Return>", self._commit_rename)
        self._rename_entry.bind("<Escape>", self._cancel_rename)
        self._rename_entry.bind("<FocusOut>", self._commit_rename)

    def _commit_rename(self, _: Any = None) -> None:
        new_title = getattr(self, "_entry_var", ctk.StringVar()).get().strip()
        self._cancel_rename()
        if new_title and self._on_rename:
            self._on_rename(new_title)
            self.update_title(new_title)

    def _cancel_rename(self, _: Any = None) -> None:
        if hasattr(self, "_rename_entry"):
            self._rename_entry.destroy()
            del self._rename_entry
        self._title_lbl.pack(side="left", padx=(6, 0), pady=10)
