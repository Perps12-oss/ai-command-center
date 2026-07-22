"""Navigation sidebar — translucent glass + cyan pill active state."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.nav_group import NavGroup
from ai_command_center.ui.design_system import theme_v2 as T

NAV_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Workspaces", (
        ("command_center", "Command Center"),
        ("workspace", "Workspace"),
        ("brain", "Brain Inspector"),
    )),
    ("Ops", (
        ("chat", "Chat"),
        ("executions", "Execution Center"),
        ("goals", "Goal Dashboard"),
        ("agents", "Agent Monitor"),
        ("approvals", "Approval Center"),
    )),
    ("Monitor", (
        ("timeline", "Timeline"),
        ("workflow", "Workflow"),
        ("automation", "Automation"),
        ("world_explorer", "World Model"),
    )),
    ("Library", (
        ("relationships", "Relationships"),
        ("dependencies", "Dependencies"),
        ("providers", "Providers"),
        ("capabilities", "Capabilities"),
        ("artifacts", "Artifacts"),
        ("notes", "Notes"),
        ("memory", "Memory"),
        ("system", "System"),
        ("plugins", "Plugins"),
    )),
    ("Settings", (
        ("settings", "Settings"),
    )),
)

NAV_ITEMS: tuple[tuple[str, str], ...] = tuple(
    item for _, items in NAV_GROUPS for item in items
)


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
        self._on_navigate = on_navigate
        self._rows: dict[str, ctk.CTkFrame] = {}
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._groups: dict[str, NavGroup] = {}
        self._active = "command_center"

        ctk.CTkLabel(
            self,
            text="AI Assistant",
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 8))

        for group_name, items in NAV_GROUPS:
            group = NavGroup(
                self,
                title=group_name,
                items=items,
                on_select=self._select,
            )
            group.pack(fill="x")
            self._groups[group_name] = group
            self._buttons.update(group.buttons)

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

        self.set_active(self._active)

    def _select(self, view_id: str) -> None:
        self._active = view_id
        self.set_active(view_id)
        self._on_navigate(view_id)

    def set_active(self, view_id: str) -> None:
        self._active = view_id
        for group in self._groups.values():
            group.set_active(view_id)

    def toggle_group(self, group_name: str) -> None:
        group = self._groups.get(group_name)
        if group is not None:
            group.toggle()

    def set_group_expanded(self, group_name: str, expanded: bool) -> None:
        group = self._groups.get(group_name)
        if group is not None:
            group.set_expanded(expanded)

    def toggle_collapse(self) -> None:
        if self.winfo_width() > 60:
            self.configure(width=48)
            for group in self._groups.values():
                group.set_compact(True)
        else:
            self.configure(width=T.SIDEBAR_WIDTH)
            for group in self._groups.values():
                group.set_compact(False)
