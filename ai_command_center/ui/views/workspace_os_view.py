"""Workspace OS view — inspector, workspace/card/resource management, timeline feed."""
from __future__ import annotations

from collections import deque
from typing import Callable

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T

_MAX_ACTIVITY = 20

_RESOURCE_ICONS = {
    "url": "🌐",
    "folder": "📁",
    "command": "⚡",
}


class _StatCard(ctk.CTkFrame):
    """Small counter card for the inspector."""

    def __init__(self, master, title: str) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
        )
        self._value = ctk.CTkLabel(
            self,
            text="0",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
            anchor="center",
        )
        self._value.pack(fill="x", padx=16, pady=(10, 0))
        ctk.CTkLabel(
            self,
            text=title,
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            anchor="center",
        ).pack(fill="x", padx=16, pady=(0, 10))

    def set(self, value: int) -> None:
        self._value.configure(text=str(value))


class _ActivityFeed(ctk.CTkFrame):
    """Human-readable timeline activity feed."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self._entries: deque[tuple[str, str]] = deque(maxlen=_MAX_ACTIVITY)
        self._rows: list[ctk.CTkFrame] = []
        self._build()

    def _build(self) -> None:
        for row in self._rows:
            row.destroy()
        self._rows.clear()

        if not self._entries:
            placeholder = ctk.CTkFrame(self, fg_color="transparent")
            placeholder.pack(fill="x", pady=6)
            ctk.CTkLabel(
                placeholder,
                text="No activity yet — create a workspace to get started.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x")
            self._rows.append(placeholder)
            return

        for icon, text in self._entries:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", pady=(3, 0))
            ctk.CTkLabel(
                row,
                text=icon,
                font=T.FONT_SMALL,
                text_color=T.ACCENT_DEFAULT,
                width=22,
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=text,
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                wraplength=560,
                justify="left",
            ).pack(side="left", fill="x", expand=True, padx=(4, 0))
            self._rows.append(row)

    def set(self, events: list[str]) -> None:
        self._entries.clear()
        for event in events:
            icon = "◈"
            lower = event.lower()
            if "workspace" in lower:
                icon = "🗂️"
            elif "card" in lower:
                icon = "🃏"
            elif "resource" in lower or "launch" in lower or "open" in lower or "execute" in lower:
                icon = "🚀"
            self._entries.appendleft((icon, event))
        self._build()

    def add(self, text: str) -> None:
        icon = "◈"
        lower = text.lower()
        if "workspace" in lower:
            icon = "🗂️"
        elif "card" in lower:
            icon = "🃏"
        elif "resource" in lower or "launch" in lower or "open" in lower or "execute" in lower:
            icon = "🚀"
        self._entries.appendleft((icon, text))
        self._build()


class _ListFrame(ctk.CTkFrame):
    """Reusable list with a search filter and action buttons."""

    def __init__(
        self,
        master,
        title: str,
        on_select: Callable[[str], None] | None = None,
        on_action: Callable[[str, str], None] | None = None,
        action_text: str = "Open",
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_select = on_select
        self._on_action = on_action
        self._action_text = action_text
        self._items: list[tuple[str, str, str]] = []
        self._filter = ""

        ctk.CTkLabel(
            self,
            text=title,
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(8, 4))

        self._search = ctk.CTkEntry(
            self,
            placeholder_text="Filter…",
            font=T.FONT_BODY,
            height=28,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._search.pack(fill="x", pady=(0, 6))
        self._search.bind("<KeyRelease>", lambda _e: self._apply_filter())

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=T.BG_DEEP, height=160)
        self._scroll.pack(fill="both", expand=True)

    def set_items(self, items: list[tuple[str, str, str]]) -> None:
        """Items are (id, title, subtitle)."""
        self._items = items
        self._apply_filter()

    def _apply_filter(self) -> None:
        self._filter = self._search.get().strip().lower()
        for child in self._scroll.winfo_children():
            child.destroy()

        filtered = [
            item for item in self._items
            if not self._filter or self._filter in item[1].lower() or self._filter in item[2].lower()
        ]
        if not filtered:
            ctk.CTkLabel(
                self._scroll,
                text="No items",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(pady=12)
            return

        for item_id, title, subtitle in filtered:
            row = ctk.CTkFrame(self._scroll, fg_color=T.BG_GLASS, corner_radius=T.CARD_RADIUS)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text=title,
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=10, pady=6)
            if self._on_action is not None:
                ctk.CTkButton(
                    row,
                    text=self._action_text,
                    width=60,
                    height=24,
                    font=(T.FONT_FAMILY, 10),
                    fg_color=T.ACCENT_DEFAULT,
                    hover_color=T.ACCENT_HOVER,
                    text_color="white",
                    corner_radius=T.SMALL_RADIUS,
                    command=lambda i=item_id: self._on_action(i, "action"),
                ).pack(side="right", padx=(0, 8), pady=6)
            if self._on_select is not None:
                row.bind("<Button-1>", lambda _e, i=item_id: self._on_select(i))
                for child in row.winfo_children():
                    if not isinstance(child, ctk.CTkButton):
                        child.bind("<Button-1>", lambda _e, i=item_id: self._on_select(i))


class WorkspaceOsView(ctk.CTkFrame):
    """Workspace OS inspector and management UI.

    Public API:
      load_from_appstate(snap) — render from AppState projection
      on_workspace_event(text) — append a human-readable timeline entry
    """

    def __init__(
        self,
        master,
        on_create_workspace: Callable[[str], None],
        on_rename_workspace: Callable[[str, str], None],
        on_create_card: Callable[[str, str], None],
        on_create_resource: Callable[[str, str, str, str], None],
        on_update_resource: Callable[[str, str, str, str], None],
        on_delete_resource: Callable[[str, str], None],
        on_launch_resource: Callable[[str, str, str], None],
        on_search: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_create_workspace = on_create_workspace
        self._on_rename_workspace = on_rename_workspace
        self._on_create_card = on_create_card
        self._on_create_resource = on_create_resource
        self._on_update_resource = on_update_resource
        self._on_delete_resource = on_delete_resource
        self._on_launch_resource = on_launch_resource
        self._on_search = on_search

        self._workspaces: list[tuple[str, str, list[str]]] = []
        self._cards: list[tuple[str, str]] = []
        self._resources: list[tuple[str, str, str, str, str]] = []
        self._selected_workspace_id: str = ""
        self._selected_card_id: str = ""
        self._selected_resource_id: str = ""

        self._build()

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        # Header
        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))
        ctk.CTkLabel(
            header,
            text="🗂️  Workspace OS",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="Ctrl+Shift+W · Create · Organize · Search · Launch · Observe",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(side="right")

        # Inspector
        inspector_card = GlassCard(scroll)
        inspector_card.pack(fill="x", padx=T.PAD, pady=(0, 8))
        ctk.CTkLabel(
            inspector_card,
            text="INSPECTOR",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        stats = ctk.CTkFrame(inspector_card, fg_color="transparent")
        stats.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        stats.columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="stat")
        self._stat_entities = _StatCard(stats, "Entities")
        self._stat_entities.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self._stat_relationships = _StatCard(stats, "Relationships")
        self._stat_relationships.grid(row=0, column=1, sticky="nsew", padx=4)
        self._stat_actions = _StatCard(stats, "Actions")
        self._stat_actions.grid(row=0, column=2, sticky="nsew", padx=4)
        self._stat_events = _StatCard(stats, "Timeline")
        self._stat_events.grid(row=0, column=3, sticky="nsew", padx=4)
        self._stat_entities_value = _StatCard(stats, "Workspace Entities")
        self._stat_entities_value.grid(row=0, column=4, sticky="nsew", padx=(4, 0))

        # Recent activity
        ctk.CTkLabel(
            inspector_card,
            text="RECENT ACTIVITY",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(8, 4))
        self._activity = _ActivityFeed(inspector_card)
        self._activity.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # Registered actions
        ctk.CTkLabel(
            inspector_card,
            text="REGISTERED ACTIONS",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(8, 4))
        self._actions_lbl = ctk.CTkLabel(
            inspector_card,
            text="—",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
            wraplength=900,
            justify="left",
        )
        self._actions_lbl.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # Two-column management
        mgmt = ctk.CTkFrame(scroll, fg_color="transparent")
        mgmt.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        mgmt.columnconfigure(0, weight=1, uniform="col")
        mgmt.columnconfigure(1, weight=1, uniform="col")

        # Workspaces
        ws_card = GlassCard(mgmt)
        ws_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        self._build_workspace_section(ws_card)

        # Cards
        card_card = GlassCard(mgmt)
        card_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        self._build_card_section(card_card)

        # Resources
        res_card = GlassCard(scroll)
        res_card.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))
        self._build_resource_section(res_card)

    def _build_workspace_section(self, card: GlassCard) -> None:
        ctk.CTkLabel(
            card,
            text="WORKSPACES",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=T.PAD, pady=(0, 6))
        self._ws_title = ctk.CTkEntry(
            row,
            placeholder_text="New workspace title",
            font=T.FONT_BODY,
            height=28,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._ws_title.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            row,
            text="Create",
            width=70,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="white",
            corner_radius=T.SMALL_RADIUS,
            command=self._create_workspace,
        ).pack(side="right")

        self._workspace_list = _ListFrame(
            card,
            "Workspaces",
            on_select=self._select_workspace,
            on_action=self._rename_workspace,
            action_text="Rename",
        )
        self._workspace_list.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def _build_card_section(self, card: GlassCard) -> None:
        ctk.CTkLabel(
            card,
            text="CARDS",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._card_ws_lbl = ctk.CTkLabel(
            card,
            text="Select a workspace",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._card_ws_lbl.pack(fill="x", padx=T.PAD, pady=(0, 4))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=T.PAD, pady=(0, 6))
        self._card_title = ctk.CTkEntry(
            row,
            placeholder_text="New card title",
            font=T.FONT_BODY,
            height=28,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._card_title.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            row,
            text="Create",
            width=70,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="white",
            corner_radius=T.SMALL_RADIUS,
            command=self._create_card,
        ).pack(side="right")

        self._card_list = _ListFrame(
            card,
            "Cards in selected workspace",
            on_select=self._select_card,
        )
        self._card_list.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def _build_resource_section(self, card: GlassCard) -> None:
        ctk.CTkLabel(
            card,
            text="RESOURCES",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._res_card_lbl = ctk.CTkLabel(
            card,
            text="Select a card to add resources",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
        )
        self._res_card_lbl.pack(fill="x", padx=T.PAD, pady=(0, 4))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=T.PAD, pady=(0, 6))
        form.columnconfigure(0, weight=3)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=3)
        form.columnconfigure(3, weight=1)

        self._res_title = ctk.CTkEntry(
            form,
            placeholder_text="Title",
            font=T.FONT_BODY,
            height=28,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._res_title.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._res_type = ctk.CTkOptionMenu(
            form,
            values=["url", "folder", "command"],
            font=T.FONT_BODY,
            height=28,
            fg_color=T.BG_INPUT,
            button_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._res_type.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self._res_value = ctk.CTkEntry(
            form,
            placeholder_text="URL / folder path / command",
            font=T.FONT_BODY,
            height=28,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._res_value.grid(row=0, column=2, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            form,
            text="Save",
            width=70,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="white",
            corner_radius=T.SMALL_RADIUS,
            command=self._save_resource,
        ).grid(row=0, column=3, sticky="e")

        self._resource_list = _ListFrame(
            card,
            "Resources",
            on_select=self._select_resource,
            on_action=self._launch_resource,
            action_text="Launch",
        )
        self._resource_list.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        ctk.CTkButton(
            btn_row,
            text="Edit Selected",
            width=90,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="white",
            corner_radius=T.SMALL_RADIUS,
            command=self._edit_selected_resource,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_row,
            text="Delete Selected",
            width=100,
            height=28,
            font=T.FONT_SMALL,
            fg_color=T.STATUS_ERROR,
            hover_color="#B91C1C",
            text_color="white",
            corner_radius=T.SMALL_RADIUS,
            command=self._delete_selected_resource,
        ).pack(side="left")

    # ── callbacks ──────────────────────────────────────────────────────────────

    def _create_workspace(self) -> None:
        title = self._ws_title.get().strip()
        if title and self._on_create_workspace is not None:
            self._on_create_workspace(title)
            self._ws_title.delete(0, "end")

    def _select_workspace(self, workspace_id: str) -> None:
        self._selected_workspace_id = workspace_id
        title = next((t for i, t in self._workspaces if i == workspace_id), "")
        self._card_ws_lbl.configure(text=f"Workspace: {title or workspace_id}")
        self._res_card_lbl.configure(text="Select a card to add resources")
        self._selected_card_id = ""
        self._refresh_cards()
        self._refresh_resources()

    def _rename_workspace(self, workspace_id: str, _action: str) -> None:
        dialog = ctk.CTkInputDialog(text="Rename workspace:", title="Rename")
        new_title = dialog.get_input()
        if new_title and self._on_rename_workspace is not None:
            self._on_rename_workspace(workspace_id, new_title.strip())

    def _create_card(self) -> None:
        title = self._card_title.get().strip()
        if not title:
            return
        if not self._selected_workspace_id:
            self._card_ws_lbl.configure(text="Select a workspace first", text_color=T.STATUS_ERROR)
            return
        if self._on_create_card is not None:
            self._on_create_card(title, self._selected_workspace_id)
            self._card_title.delete(0, "end")

    def _select_card(self, card_id: str) -> None:
        self._selected_card_id = card_id
        title = next((t for i, t in self._cards if i == card_id), "")
        self._res_card_lbl.configure(text=f"Card: {title or card_id}")
        self._refresh_resources()

    def _save_resource(self) -> None:
        title = self._res_title.get().strip()
        resource_type = self._res_type.get()
        value = self._res_value.get().strip()
        if not title or not value:
            return
        if not self._selected_card_id:
            self._res_card_lbl.configure(text="Select a card first", text_color=T.STATUS_ERROR)
            return
        if self._selected_resource_id:
            if self._on_update_resource is not None:
                self._on_update_resource(self._selected_resource_id, title, resource_type, value)
        else:
            if self._on_create_resource is not None:
                self._on_create_resource(title, resource_type, value, self._selected_card_id)
        self._res_title.delete(0, "end")
        self._res_value.delete(0, "end")
        self._selected_resource_id = ""

    def _select_resource(self, resource_id: str) -> None:
        self._selected_resource_id = resource_id
        res = next((r for r in self._resources if r[0] == resource_id), None)
        if res:
            self._res_title.delete(0, "end")
            self._res_title.insert(0, res[1])
            self._res_type.set(res[2])
            self._res_value.delete(0, "end")
            self._res_value.insert(0, res[3])

    def _launch_resource(self, resource_id: str, _action: str) -> None:
        res = next((r for r in self._resources if r[0] == resource_id), None)
        if res and self._on_launch_resource is not None:
            self._on_launch_resource(resource_id, res[2], res[3])

    def _edit_selected_resource(self) -> None:
        if self._selected_resource_id:
            self._select_resource(self._selected_resource_id)
        else:
            self._res_card_lbl.configure(text="Select a resource first", text_color=T.STATUS_ERROR)

    def _delete_selected_resource(self) -> None:
        if self._selected_resource_id and self._on_delete_resource is not None:
            self._on_delete_resource(self._selected_resource_id, self._selected_card_id)
            self._res_title.delete(0, "end")
            self._res_value.delete(0, "end")
            self._selected_resource_id = ""

    # ── AppState rendering ───────────────────────────────────────────────────────

    def load_from_appstate(self, snap) -> None:
        """Render the entire view from the AppState workspace_os projection."""
        ws = snap.workspace_os
        self._stat_entities.set(ws.entity_count)
        self._stat_relationships.set(ws.relationship_count)
        self._stat_actions.set(ws.action_count)
        self._stat_events.set(ws.event_count)

        # Count entities that belong to workspaces
        ws_entities = sum(
            1 for e in ws.entities
            if e.entity_type in ("workspace", "card", "resource")
        )
        self._stat_entities_value.set(ws_entities)

        # Registered actions
        if ws.actions:
            self._actions_lbl.configure(text="  ·  ".join(ws.actions))
        else:
            self._actions_lbl.configure(text="No actions registered yet")

        # Activity feed
        self._activity.set(list(ws.recent_events))

        # Store entity lists
        self._workspaces = [
            (
                e.entity_id,
                e.title,
                [
                    str(item)
                    for item in (dict(e.metadata).get("entities") or [])
                    if item
                ],
            )
            for e in ws.entities
            if e.entity_type == "workspace"
        ]
        self._cards = [
            (e.entity_id, e.title)
            for e in ws.entities
            if e.entity_type == "card"
        ]
        self._resources = [
            (
                e.entity_id,
                e.title,
                dict(e.metadata).get("resource_type", "url"),
                dict(e.metadata).get("url")
                or dict(e.metadata).get("path")
                or dict(e.metadata).get("command")
                or "",
                dict(e.metadata).get("description", ""),
            )
            for e in ws.entities
            if e.entity_type == "resource"
        ]

        self._refresh_workspaces()
        self._refresh_cards()
        self._refresh_resources()

    def _refresh_workspaces(self) -> None:
        items = [(i, t, "") for i, t, _ in self._workspaces]
        self._workspace_list.set_items(items)
        if self._selected_workspace_id and not any(i == self._selected_workspace_id for i, _, _ in self._workspaces):
            self._selected_workspace_id = ""

    def _refresh_cards(self) -> None:
        if self._selected_workspace_id:
            ws = next((w for w in self._workspaces if w[0] == self._selected_workspace_id), None)
            workspace_ids = set(ws[2]) if ws else set()
            items = [
                (i, t, "") for i, t in self._cards
                if i in workspace_ids or not workspace_ids
            ]
        else:
            items = []
        self._card_list.set_items(items)
        if self._selected_card_id and not any(i == self._selected_card_id for i, _ in self._cards):
            self._selected_card_id = ""

    def _refresh_resources(self) -> None:
        if self._selected_card_id:
            items = [
                (i, f"{_RESOURCE_ICONS.get(r, '◈')} {t}", r)
                for i, t, r, v, _ in self._resources
            ]
        else:
            items = []
        self._resource_list.set_items(items)

    def on_workspace_event(self, text: str) -> None:
        """Append a timeline event to the visible activity feed."""
        self._activity.add(text)
