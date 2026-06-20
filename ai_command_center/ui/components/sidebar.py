"""Navigation sidebar — icons + accent-bar indicator + collapse toggle."""
from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T

NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("home",     "⌂",  "Home"),
    ("chat",     "💬", "Chat"),
    ("notes",    "📝", "Notes"),
    ("memory",   "🧠", "Memory"),
    ("system",   "⚙",  "System"),
    ("plugins",  "🧩", "Plugins"),
    ("settings", "◈",  "Settings"),
)

_COLLAPSED_W = 52
_EXPANDED_W  = T.SIDEBAR_WIDTH


class _NavButton(ctk.CTkFrame):
    """Single nav item — accent bar on left when active, collapse-aware."""

    BAR_W = 3

    def __init__(self, master, icon: str, label: str, command) -> None:
        super().__init__(master, fg_color="transparent", height=40)
        self.pack_propagate(False)
        self._icon  = icon
        self._label = label

        self._bar = ctk.CTkFrame(
            self, width=self.BAR_W, fg_color="transparent", corner_radius=0
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
            self._btn.configure(fg_color=T.BG_GLASS, text_color=T.TEXT_PRIMARY)
        else:
            self._bar.configure(fg_color="transparent")
            self._btn.configure(fg_color="transparent", text_color=T.TEXT_MUTED)

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed:
            self._btn.configure(
                text=f"  {self._icon}",
                anchor="center",
            )
        else:
            self._btn.configure(
                text=f" {self._icon}  {self._label}",
                anchor="w",
            )


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, **kwargs) -> None:
        super().__init__(
            master,
            width=_EXPANDED_W,
            fg_color=T.BG_PANEL,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._nav_buttons: dict[str, _NavButton] = {}
        self._active      = "home"
        self._collapsed   = False
        self._on_navigate = on_navigate

        # ── Brand header ───────────────────────────────────────────────────────
        self._brand = ctk.CTkFrame(self, fg_color="transparent")
        self._brand.pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._brand_icon = ctk.CTkLabel(
            self._brand,
            text="◇",
            font=(T.FONT_FAMILY, 18, "bold"),
            text_color=T.ACCENT_DEFAULT,
        )
        self._brand_icon.pack(side="left")

        self._brand_text = ctk.CTkLabel(
            self._brand,
            text=" Command",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        )
        self._brand_text.pack(side="left")

        self._sub_text = ctk.CTkLabel(
            self,
            text="Center",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._sub_text.pack(anchor="w", padx=T.PAD, pady=(0, 12))

        # ── Divider ────────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=T.BG_GLASS_BORDER).pack(
            fill="x", padx=8, pady=(0, 8)
        )

        # ── Nav items ──────────────────────────────────────────────────────────
        for view_id, icon, label in NAV_ITEMS:
            btn = _NavButton(
                self,
                icon,
                label,
                command=lambda v=view_id: self._select(v),
            )
            btn.pack(fill="x", pady=1)
            self._nav_buttons[view_id] = btn

        self._refresh()

        # ── Spacer ─────────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        # ── Footer ─────────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=T.BG_GLASS_BORDER).pack(
            fill="x", padx=8, pady=(0, 4)
        )

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=8, pady=(0, T.PAD))

        self._toggle_btn = ctk.CTkButton(
            footer,
            text="⟨",
            width=28,
            height=24,
            font=(T.FONT_FAMILY, 13),
            fg_color="transparent",
            hover_color=T.BG_GLASS,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self.toggle_collapse,
        )
        self._toggle_btn.pack(side="left")

        self._version_lbl = ctk.CTkLabel(
            footer,
            text="Phase 5B",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._version_lbl.pack(side="left", padx=(6, 0))

    # ── collapse ───────────────────────────────────────────────────────────────

    def toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.configure(width=_COLLAPSED_W)
            self._brand_text.configure(text="")
            self._sub_text.configure(text="")
            self._version_lbl.configure(text="")
            self._toggle_btn.configure(text="⟩")
        else:
            self.configure(width=_EXPANDED_W)
            self._brand_text.configure(text=" Command")
            self._sub_text.configure(text="Center")
            self._version_lbl.configure(text="Phase 5B")
            self._toggle_btn.configure(text="⟨")
        for btn in self._nav_buttons.values():
            btn.set_collapsed(self._collapsed)

    # ── internal ───────────────────────────────────────────────────────────────

    def _select(self, view_id: str) -> None:
        self._active = view_id
        self._refresh()
        self._on_navigate(view_id)

    def _refresh(self) -> None:
        for vid, btn in self._nav_buttons.items():
            btn.set_active(vid == self._active)

    def set_active(self, view_id: str) -> None:
        self._active = view_id
        self._refresh()
