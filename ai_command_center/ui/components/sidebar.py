"""Navigation sidebar — translucent glass + cyan pill active state."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

NAV_ITEMS: tuple[tuple[str, str], ...] = (
    ("workspace", "Workspace"),
    ("command_center", "Command Center"),
    ("home", "Home"),
    ("chat", "Chat"),
    ("executions", "Execution Center"),
    ("timeline", "Timeline"),
    ("workflow", "Workflow"),
    ("automation", "Automation"),
    ("world_explorer", "World Model"),
    ("relationships", "Relationships"),
    ("dependencies", "Dependencies"),
    ("providers", "Providers"),
    ("capabilities", "Capabilities"),
    ("artifacts", "Artifacts"),
    ("notes", "Notes"),
    ("memory", "Memory"),
    ("system", "System"),
    ("plugins", "Plugins"),
    ("settings", "Settings"),
    ("goals", "Goal Dashboard"),
    ("agents", "Agent Monitor"),
    ("approvals", "Approval Center"),
)

# Feature-flagged nav items — registered dynamically if feature is enabled
FEATURE_NAV_ITEMS: dict[str, tuple[str, str]] = {
    "capabilities": ("capabilities", "Capabilities"),
    "providers":    ("providers",    "Providers"),
    "artifacts":    ("artifacts",    "Artifacts"),
}


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, **kwargs) -> None:
        super().__init__(
            master,
            width=T.SIDEBAR_WIDTH,
            fg_color="transparent",
            border_width=0,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._rows: dict[str, ctk.CTkFrame] = {}
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._active = "home"

        ctk.CTkLabel(
            self,
            text="AI Assistant",
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 8))

        for view_id, label in NAV_ITEMS:
            row = ctk.CTkFrame(self, fg_color="transparent", height=40)
            row.pack(fill="x", padx=8, pady=2)
            row.pack_propagate(False)

            btn = ctk.CTkButton(
                row,
                text=label,
                anchor="w",
                font=T.FONT_BODY,
                fg_color="transparent",
                text_color=T.TEXT_SECONDARY,
                hover_color=T.LIGHT_GLASS,
                height=36,
                corner_radius=T.CORNER_RADIUS,
                command=lambda v=view_id: self._select(v, on_navigate),
            )
            btn.pack(fill="both", expand=True, padx=4)
            self._rows[view_id] = row
            self._buttons[view_id] = btn

        user = ctk.CTkFrame(
            self,
            fg_color=T.GLASS_BG,
            corner_radius=T.PILL_RADIUS,
            border_width=1,
            border_color=T.GLASS_BORDER,
        )
        user.pack(side="bottom", fill="x", padx=T.PAD, pady=T.PAD)
        ctk.CTkLabel(
            user,
            text="Local User",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=10)

        self._highlight()

    def _select(self, view_id: str, on_navigate) -> None:
        self._active = view_id
        self._highlight()
        on_navigate(view_id)

    def _highlight(self) -> None:
        for vid, btn in self._buttons.items():
            if vid == self._active:
                btn.configure(
                    fg_color=T.HERO_CYAN_DIM,
                    text_color=T.HERO_CYAN,
                    border_width=0,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=T.TEXT_SECONDARY,
                    border_width=0,
                )

    def set_active(self, view_id: str) -> None:
        self._active = view_id
        self._highlight()

    def toggle_collapse(self) -> None:
        if self.winfo_width() > 60:
            self.configure(width=48)
            for btn in self._buttons.values():
                btn.configure(text="", width=28)
        else:
            self.configure(width=T.SIDEBAR_WIDTH)
            labels = dict(NAV_ITEMS)
            for vid, btn in self._buttons.items():
                btn.configure(text=labels.get(vid, vid), width=0)
