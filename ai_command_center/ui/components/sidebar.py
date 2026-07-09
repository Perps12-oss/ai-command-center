"""Navigation sidebar — purple active state with icons."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("workspace", "▦", "Workspace"),
    ("home", "⌂", "Home"),
    ("chat", "💬", "Chat"),
    ("executions", "⚡", "Executions"),
    ("providers", "🔌", "Providers"),
    ("capabilities", "🧩", "Capabilities"),
    ("artifacts", "📦", "Artifacts"),
    ("notes", "📝", "Notes"),
    ("memory", "🧠", "Memory"),
    ("system", "⚙", "System"),
    ("plugins", "🔧", "Plugins"),
    ("settings", "◈", "Settings"),
)

FEATURE_NAV_ITEMS: dict[str, tuple[str, str, str]] = {
    "capabilities": ("capabilities", "🧩", "Capabilities"),
    "providers": ("providers", "🔌", "Providers"),
    "artifacts": ("artifacts", "📦", "Artifacts"),
}


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, **kwargs) -> None:
        super().__init__(
            master,
            width=T.SIDEBAR_WIDTH,
            fg_color=T.SURFACE_PRIMARY,
            border_width=0,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._rows: dict[str, ctk.CTkFrame] = {}
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._active = "home"
        self._labels: dict[str, str] = {}

        ctk.CTkLabel(
            self,
            text="AI Assistant",
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 8))

        for view_id, icon, label in NAV_ITEMS:
            self._labels[view_id] = label
            row = ctk.CTkFrame(self, fg_color="transparent", height=40)
            row.pack(fill="x", padx=8, pady=2)
            row.pack_propagate(False)

            btn = ctk.CTkButton(
                row,
                text=f"  {icon}  {label}",
                anchor="w",
                font=T.FONT_BODY,
                fg_color="transparent",
                text_color=T.TEXT_SECONDARY,
                hover_color=T.SURFACE_ELEVATED,
                height=36,
                corner_radius=12,
                command=lambda v=view_id: self._select(v, on_navigate),
            )
            btn.pack(fill="both", expand=True, padx=4)
            self._rows[view_id] = row
            self._buttons[view_id] = btn

        user = ctk.CTkFrame(
            self,
            fg_color=T.SURFACE_ELEVATED,
            corner_radius=T.PILL_RADIUS,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
        )
        user.pack(side="bottom", fill="x", padx=T.PAD, pady=T.PAD)

        user_row = ctk.CTkFrame(user, fg_color="transparent")
        user_row.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(
            user_row,
            text="●",
            font=(T.FONT_FAMILY, 8),
            text_color=T.SUCCESS_GREEN,
            width=12,
        ).pack(side="left")

        info = ctk.CTkFrame(user_row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=(6, 0))

        ctk.CTkLabel(
            info,
            text="Local User",
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            info,
            text="Online",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")

        self._highlight()

    def _select(self, view_id: str, on_navigate) -> None:
        self._active = view_id
        self._highlight()
        on_navigate(view_id)

    def _highlight(self) -> None:
        for vid, btn in self._buttons.items():
            label = self._labels.get(vid, vid)
            icon = next((i for v, i, _ in NAV_ITEMS if v == vid), "")
            if vid == self._active:
                btn.configure(
                    fg_color=T.SURFACE_ELEVATED,
                    text_color=T.ACCENT_PURPLE,
                    border_width=1,
                    border_color="#3B3B8C",
                    text=f"  {icon}  {label}",
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=T.TEXT_SECONDARY,
                    border_width=0,
                    text=f"  {icon}  {label}",
                )

    def set_active(self, view_id: str) -> None:
        self._active = view_id
        self._highlight()

    def toggle_collapse(self) -> None:
        if self.winfo_width() > 60:
            self.configure(width=48)
            for vid, btn in self._buttons.items():
                icon = next((i for v, i, _ in NAV_ITEMS if v == vid), "")
                btn.configure(text=icon, width=28)
        else:
            self.configure(width=T.SIDEBAR_WIDTH)
            for vid, btn in self._buttons.items():
                label = self._labels.get(vid, vid)
                icon = next((i for v, i, _ in NAV_ITEMS if v == vid), "")
                btn.configure(text=f"  {icon}  {label}", width=0)
