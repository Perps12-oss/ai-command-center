"""Navigation sidebar — Mission Control information architecture.

Groups (Priority 5):
  Workspace · Knowledge · Monitoring · System

Adds: collapsible groups, search, notification badges, active indicators,
favorites, and recent pages.
"""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.nav_group import NavGroup
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.mission_control.layout_prefs import LayoutPrefs

NAV_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Workspace", (
        ("command_center", "Dashboard"),
        ("workspace", "Workspace"),
        ("chat", "Chat"),
        ("goals", "Goals"),
        ("executions", "Execution"),
        ("agents", "Agents"),
        ("approvals", "Approvals"),
    )),
    ("Knowledge", (
        ("world_explorer", "World Model"),
        ("brain", "Brain"),
        ("relationships", "Relationships"),
        ("memory", "Memory"),
        ("notes", "Notes"),
        ("graph_workspace", "Graph Workspace"),
    )),
    ("Monitoring", (
        ("timeline", "Timeline"),
        ("workflow", "Workflow"),
        ("automation", "Automation"),
        ("operations", "Operations"),
        ("evidence", "Logs"),
        ("insights", "Insights"),
    )),
    ("System", (
        ("providers", "Providers"),
        ("dependencies", "Dependencies"),
        ("capabilities", "Capabilities"),
        ("artifacts", "Artifacts"),
        ("plugins", "Plugins"),
        ("system", "System"),
        ("settings", "Settings"),
    )),
)

NAV_ITEMS: tuple[tuple[str, str], ...] = tuple(
    item for _, items in NAV_GROUPS for item in items
)

_LABEL_BY_ID: dict[str, str] = {vid: label for vid, label in NAV_ITEMS}


class Sidebar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_navigate,
        layout_prefs: LayoutPrefs | None = None,
        **kwargs,
    ) -> None:
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
        self._prefs = layout_prefs or LayoutPrefs()
        self._rows: dict[str, ctk.CTkFrame] = {}
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._groups: dict[str, NavGroup] = {}
        self._badges: dict[str, int] = {}
        self._active = "command_center"
        self._filter = ""
        self._compact = False

        ctk.CTkLabel(
            self,
            text="Mission Control",
            font=T.FONT_HEADER,
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 4))

        self._search = ctk.CTkEntry(
            self,
            placeholder_text="Search pages…",
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.BG_INPUT,
            border_color=T.GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._search.pack(fill="x", padx=T.PAD, pady=(0, 8))
        self._search.bind("<KeyRelease>", self._on_search)

        self._favorites_host = ctk.CTkFrame(self, fg_color="transparent")
        self._favorites_host.pack(fill="x", padx=T.PAD, pady=(0, 4))
        self._favorites_label = ctk.CTkLabel(
            self._favorites_host,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._favorites_label.pack(fill="x")

        self._recent_host = ctk.CTkFrame(self, fg_color="transparent")
        self._recent_host.pack(fill="x", padx=T.PAD, pady=(0, 4))
        self._recent_label = ctk.CTkLabel(
            self._recent_host,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._recent_label.pack(fill="x")

        self._nav_host = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._nav_host.pack(fill="both", expand=True)

        for group_name, items in NAV_GROUPS:
            group = NavGroup(
                self._nav_host,
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
        self._refresh_fav_recent()

    def _on_search(self, _event=None) -> None:
        self._filter = (self._search.get() or "").strip().lower()
        for group_name, items in NAV_GROUPS:
            group = self._groups[group_name]
            visible = 0
            for view_id, label in items:
                btn = group.buttons.get(view_id)
                if btn is None:
                    continue
                match = (not self._filter) or (
                    self._filter in label.lower() or self._filter in view_id.lower()
                )
                if match:
                    visible += 1
                    try:
                        btn.master.pack(fill="x", padx=8, pady=2)
                    except Exception:
                        pass
                else:
                    try:
                        btn.master.pack_forget()
                    except Exception:
                        pass
            if self._filter:
                group.set_expanded(visible > 0)
            else:
                # Clearing search must restore groups collapsed only for filtering.
                group.set_expanded(True)
            # Restore labels with badges after filter
            self._apply_badge_labels()

    def _select(self, view_id: str) -> None:
        self._active = view_id
        self.set_active(view_id)
        self._prefs.record_page(view_id)
        self._refresh_fav_recent()
        self._on_navigate(view_id)

    def set_active(self, view_id: str) -> None:
        self._active = view_id
        for group in self._groups.values():
            group.set_active(view_id)
        self._apply_badge_labels()

    def set_badge(self, view_id: str, count: int) -> None:
        """Notification badge for a nav item (0 clears)."""
        if count <= 0:
            self._badges.pop(view_id, None)
        else:
            self._badges[view_id] = count
        self._apply_badge_labels()

    def set_badges(self, badges: dict[str, int]) -> None:
        self._badges = {k: v for k, v in badges.items() if v > 0}
        self._apply_badge_labels()

    def toggle_favorite(self, view_id: str) -> None:
        self._prefs.toggle_favorite(view_id)
        self._refresh_fav_recent()

    def _apply_badge_labels(self) -> None:
        for view_id, btn in self._buttons.items():
            if self._compact:
                # Keep icon-only collapsed mode; do not restore full labels on refresh.
                btn.configure(text="")
                continue
            base = _LABEL_BY_ID.get(view_id, view_id)
            active_mark = "● " if view_id == self._active else ""
            fav = "★ " if view_id in self._prefs.favorites else ""
            count = self._badges.get(view_id, 0)
            badge = f"  ({count})" if count else ""
            btn.configure(text=f"{active_mark}{fav}{base}{badge}")

    def _refresh_fav_recent(self) -> None:
        favs = self._prefs.favorites
        if favs:
            labels = ", ".join(_LABEL_BY_ID.get(v, v) for v in favs[:4])
            self._favorites_label.configure(text=f"Favorites · {labels}")
        else:
            self._favorites_label.configure(text="Favorites · pin pages from search")
        recent = self._prefs.recent_pages
        if recent:
            labels = ", ".join(_LABEL_BY_ID.get(v, v) for v in recent[:4])
            self._recent_label.configure(text=f"Recent · {labels}")
        else:
            self._recent_label.configure(text="Recent · navigate to populate")

    def toggle_group(self, group_name: str) -> None:
        group = self._groups.get(group_name)
        if group is not None:
            group.toggle()

    def set_group_expanded(self, group_name: str, expanded: bool) -> None:
        group = self._groups.get(group_name)
        if group is not None:
            group.set_expanded(expanded)

    def toggle_collapse(self) -> None:
        if not self._compact:
            self.configure(width=48)
            self._compact = True
            for group in self._groups.values():
                group.set_compact(True)
        else:
            self.configure(width=T.SIDEBAR_WIDTH)
            self._compact = False
            for group in self._groups.values():
                group.set_compact(False)
            self._apply_badge_labels()
