"""Navigation sidebar — icons + accent-bar active indicator."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T

NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("home",     "⌂",  "Home"),
    ("chat",     "💬", "Chat"),
    ("notes",    "📝", "Notes"),
    ("system",   "⚙",  "System"),
    ("plugins",  "🧩", "Plugins"),
    ("settings", "◈",  "Settings"),
)


class _NavButton(ctk.CTkFrame):
    """Single nav item with an accent bar on the left when active."""

    BAR_W = 3

    def __init__(self, master, icon: str, label: str, command) -> None:
        super().__init__(master, fg_color="transparent", height=40)
        self.pack_propagate(False)

        self._bar = ctk.CTkFrame(
            self,
            width=self.BAR_W,
            fg_color="transparent",
            corner_radius=0,
        )
        self._bar.pack(side="left", fill="y")

        self._btn = ctk.CTkButton(
            self,
            text=f" {icon}  {label}",
            anchor="w",
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color=T.TEXT_MUTED,
            hover_color=T.BG_GLASS,
            height=36,
            corner_radius=6,
            command=command,
        )
        self._btn.pack(fill="both", expand=True, padx=(2, 8))

    def set_active(self, active: bool) -> None:
        if active:
            self._bar.configure(fg_color=T.ACCENT_DEFAULT)
            self._btn.configure(
                fg_color=T.BG_GLASS,
                text_color=T.TEXT_PRIMARY,
            )
        else:
            self._bar.configure(fg_color="transparent")
            self._btn.configure(
                fg_color="transparent",
                text_color=T.TEXT_MUTED,
            )


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, **kwargs) -> None:
        super().__init__(
            master,
            width=T.SIDEBAR_WIDTH,
            fg_color=T.BG_PANEL,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._nav_buttons: dict[str, _NavButton] = {}
        self._active = "home"

        # Brand label
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        ctk.CTkLabel(
            brand,
            text="◇",
            font=(T.FONT_FAMILY, 18, "bold"),
            text_color=T.ACCENT_DEFAULT,
        ).pack(side="left")
        ctk.CTkLabel(
            brand,
            text=" Command",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            self,
            text="Center",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w", padx=T.PAD, pady=(0, 12))

        # Divider
        ctk.CTkFrame(self, height=1, fg_color=T.BG_GLASS_BORDER).pack(
            fill="x", padx=8, pady=(0, 8)
        )

        # Nav items
        for view_id, icon, label in NAV_ITEMS:
            btn = _NavButton(
                self,
                icon,
                label,
                command=lambda v=view_id: self._select(v, on_navigate),
            )
            btn.pack(fill="x", pady=1)
            self._nav_buttons[view_id] = btn

        self._refresh()

        # Spacer + version footer
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)
        ctk.CTkFrame(self, height=1, fg_color=T.BG_GLASS_BORDER).pack(
            fill="x", padx=8, pady=(0, 4)
        )
        ctk.CTkLabel(
            self,
            text="Phase 5B",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))

    def _select(self, view_id: str, on_navigate) -> None:
        self._active = view_id
        self._refresh()
        on_navigate(view_id)

    def _refresh(self) -> None:
        for vid, btn in self._nav_buttons.items():
            btn.set_active(vid == self._active)

    def set_active(self, view_id: str) -> None:
        self._active = view_id
        self._refresh()
