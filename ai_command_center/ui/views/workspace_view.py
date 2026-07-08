"""Workspace canvas — entity grid projected from AppState."""

from __future__ import annotations

import ast
from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children
from ai_command_center.ui.workspace_os_controller import WorkspaceOsUIController
from ai_command_center.ui.workspace_os_dialogs import (
    CreateCardDialog,
    CreateResourceDialog,
    CreateWorkspaceDialog,
)

_TYPE_ICON = {
    "workspace": "◈",
    "card": "▢",
    "resource": "🔗",
    "note": "📝",
}

_GROUP_ORDER: tuple[tuple[str, str], ...] = (
    ("workspace", "Workspaces"),
    ("card", "Cards"),
    ("resource", "Resources"),
    ("note", "Notes"),
)


class _EntityTile(GlassCard):
    def __init__(
        self,
        master,
        *,
        title: str,
        entity_type: str,
        subtitle: str,
        on_select: Callable[[], None] | None = None,
        on_launch: Callable[[], None] | None = None,
        on_chat: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        if on_select is not None:
            self.bind("<Button-1>", lambda _event: on_select())
        icon = _TYPE_ICON.get(entity_type, "•")
        ctk.CTkLabel(
            self,
            text=f"{icon}  {title}",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            self,
            text=entity_type.title(),
            font=T.FONT_SMALL,
            text_color=T.ACCENT_DEFAULT,
            anchor="w",
        ).pack(fill="x", padx=12)
        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
                wraplength=220,
                justify="left",
            ).pack(fill="x", padx=12, pady=(2, 0))
        if on_launch is not None or on_chat is not None:
            btn_row = ctk.CTkFrame(self, fg_color="transparent")
            btn_row.pack(anchor="w", padx=12, pady=(8, 10))
            if on_chat is not None:
                ctk.CTkButton(
                    btn_row,
                    text="Chat",
                    width=72,
                    height=28,
                    font=T.FONT_SMALL,
                    fg_color=T.BG_GLASS,
                    hover_color=T.LIGHT_GLASS,
                    border_width=1,
                    border_color=T.BG_GLASS_BORDER,
                    command=on_chat,
                ).pack(side="left", padx=(0, 6))
            if on_launch is not None:
                ctk.CTkButton(
                    btn_row,
                    text="Launch",
                    width=72,
                    height=28,
                    font=T.FONT_SMALL,
                    fg_color=T.ACCENT_DEFAULT,
                    hover_color=T.ACCENT_HOVER,
                    command=on_launch,
                ).pack(side="left")
        else:
            ctk.CTkFrame(self, fg_color="transparent", height=8).pack()


class WorkspaceView(ctk.CTkFrame):
    """Primary workspace surface — renders Workspace OS entities from AppState."""

    def __init__(
        self,
        master,
        *,
        on_launch: Callable[[dict], None],
        on_open_chat: Callable[[dict], None],
        on_command: Callable[[str], None],
        ws_controller: WorkspaceOsUIController,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_launch = on_launch
        self._on_open_chat = on_open_chat
        self._on_command = on_command
        self._ws = ws_controller
        self._entities: tuple = ()
        self._build_layout()

    def _build_layout(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        ctk.CTkLabel(
            header,
            text="Workspace",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(side="left")

        self._stats_label = ctk.CTkLabel(
            header,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="e",
        )
        self._stats_label.pack(side="right")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=T.PAD, pady=(0, 8))

        ctk.CTkButton(
            actions,
            text="+ Workspace",
            height=32,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
            command=self._show_create_workspace,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="+ Card",
            height=32,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
            command=self._show_create_card,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="+ Resource",
            height=32,
            font=T.FONT_SMALL,
            fg_color=T.BG_GLASS,
            hover_color=T.LIGHT_GLASS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
            command=self._show_create_resource,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Inspector (Ctrl+Shift+W)",
            height=32,
            font=T.FONT_SMALL,
            fg_color="transparent",
            hover_color=T.LIGHT_GLASS,
            text_color=T.TEXT_SECONDARY,
            command=lambda: self._on_command("go workspace inspector"),
        ).pack(side="left")

        self._canvas_host = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.BG_GLASS,
        )
        self._canvas_host.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def _entity_options(self, entity_type: str) -> list[tuple[str, str]]:
        return [
            (str(e.entity_id), e.title or str(e.entity_id))
            for e in self._entities
            if e.entity_type == entity_type
        ]

    def _resolve_parent_workspace_id(self, entity) -> str:
        """Resolve parent workspace for card/resource/note tiles."""
        if entity.entity_type == "workspace":
            return str(entity.entity_id)
        meta = dict(entity.metadata)
        ws = str(meta.get("workspace_id", "")).strip()
        if ws:
            return ws
        card_id = str(meta.get("card_id", "")).strip()
        if card_id:
            for candidate in self._entities:
                if candidate.entity_id == card_id:
                    return self._resolve_parent_workspace_id(candidate)
        for workspace in self._entities:
            if workspace.entity_type != "workspace":
                continue
            ws_meta = dict(workspace.metadata)
            raw = str(ws_meta.get("entities", "")).strip()
            if not raw:
                continue
            try:
                child_ids = ast.literal_eval(raw)
            except (SyntaxError, ValueError):
                continue
            if isinstance(child_ids, list) and str(entity.entity_id) in {
                str(child) for child in child_ids
            }:
                return str(workspace.entity_id)
        return ""

    def _on_tile_select(self, entity) -> None:
        workspace_id = self._resolve_parent_workspace_id(entity)
        self._ws.select_entity(
            str(entity.entity_id),
            str(entity.entity_type),
            str(entity.title or entity.entity_id),
            workspace_id=workspace_id,
        )

    def _show_create_workspace(self) -> None:
        dialog = CreateWorkspaceDialog(self.winfo_toplevel())
        self.wait_window(dialog)
        if dialog.result:
            self._ws.create_workspace(
                dialog.result["title"],
                dialog.result.get("description", ""),
            )

    def _show_create_card(self) -> None:
        workspaces = self._entity_options("workspace")
        dialog = CreateCardDialog(self.winfo_toplevel(), workspaces=workspaces)
        self.wait_window(dialog)
        if dialog.result:
            self._ws.create_card(
                dialog.result["workspace_id"],
                dialog.result["title"],
                dialog.result.get("description", ""),
            )

    def _show_create_resource(self) -> None:
        cards = self._entity_options("card")
        dialog = CreateResourceDialog(self.winfo_toplevel(), cards=cards)
        self.wait_window(dialog)
        if dialog.result:
            self._ws.create_resource(
                dialog.result["card_id"],
                dialog.result["title"],
                "url",
                dialog.result["url"],
            )

    def _render_empty_state(self) -> None:
        card = GlassCard(self._canvas_host)
        card.pack(fill="x", padx=8, pady=24)

        ctk.CTkLabel(
            card,
            text="◈",
            font=("Segoe UI", 36),
            text_color=T.ACCENT_DEFAULT,
        ).pack(pady=(24, 4))
        ctk.CTkLabel(
            card,
            text="Your workspace is empty",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            card,
            text=(
                "Create a workspace to organize cards and launchable resources.\n"
                "Use the buttons above or open the Inspector (Ctrl+Shift+W)."
            ),
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
            justify="center",
        ).pack(pady=(0, 16))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(pady=(0, 24))
        ctk.CTkButton(
            row,
            text="+ Create Workspace",
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            command=self._show_create_workspace,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            row,
            text="Open Inspector",
            fg_color="transparent",
            hover_color=T.LIGHT_GLASS,
            text_color=T.TEXT_SECONDARY,
            command=lambda: self._on_command("go workspace inspector"),
        ).pack(side="left", padx=8)

    def _render_activity(self, events: tuple[str, ...]) -> None:
        section = ctk.CTkFrame(self._canvas_host, fg_color="transparent")
        section.pack(fill="x", padx=4, pady=(0, 12))

        ctk.CTkLabel(
            section,
            text="Recent Activity",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        activity = GlassCard(section)
        activity.pack(fill="x")
        for event_text in events[-8:]:
            ctk.CTkLabel(
                activity,
                text=f"• {event_text}",
                font=T.FONT_SMALL,
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=12, pady=2)
        ctk.CTkFrame(activity, fg_color="transparent", height=6).pack()

    def _render_entity_group(
        self,
        host,
        *,
        label: str,
        entity_type: str,
        entities: list,
    ) -> None:
        section = ctk.CTkFrame(host, fg_color="transparent")
        section.pack(fill="x", padx=4, pady=(0, 12))

        ctk.CTkLabel(
            section,
            text=f"{_TYPE_ICON.get(entity_type, '•')}  {label} ({len(entities)})",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        grid = ctk.CTkFrame(section, fg_color="transparent")
        grid.pack(fill="x")
        columns = 3
        for index, entity in enumerate(entities):
            meta = dict(entity.metadata)
            subtitle = (
                meta.get("description")
                or meta.get("url")
                or meta.get("path")
                or meta.get("command")
                or ""
            )
            resource_type = meta.get("resource_type")
            value = meta.get("url") or meta.get("path") or meta.get("command") or ""
            launch: Callable[[], None] | None = None
            chat: Callable[[], None] | None = None
            if entity.entity_type == "resource" and resource_type and value:
                payload = {
                    "resource_id": entity.entity_id,
                    "resource_type": resource_type,
                    "value": value,
                }

                def _launch_handler(p: dict = payload) -> None:
                    self._on_launch(p)

                launch = _launch_handler

            chat_payload = {
                "entity_id": entity.entity_id,
                "entity_type": entity.entity_type,
                "title": entity.title or entity.entity_id,
            }
            parent_ws = self._resolve_parent_workspace_id(entity)
            if parent_ws and entity.entity_type != "workspace":
                chat_payload["workspace_id"] = parent_ws
            if meta.get("description"):
                chat_payload["description"] = str(meta["description"])
            if meta.get("url"):
                chat_payload["url"] = str(meta["url"])
            elif meta.get("path"):
                chat_payload["path"] = str(meta["path"])
            elif meta.get("command"):
                chat_payload["path"] = str(meta["command"])

            def _chat_handler(p: dict = chat_payload) -> None:
                self._on_open_chat(p)

            def _select_handler(ent=entity) -> None:
                self._on_tile_select(ent)

            chat = _chat_handler
            row, col = divmod(index, columns)
            tile = _EntityTile(
                grid,
                title=entity.title or entity.entity_id,
                entity_type=entity.entity_type,
                subtitle=str(subtitle)[:120],
                on_select=_select_handler,
                on_launch=launch,
                on_chat=chat,
            )
            tile.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1)

    def load_from_appstate(self, snap) -> None:
        ws = snap.workspace_os
        workspace_key = (
            ws.entity_count,
            ws.relationship_count,
            ws.event_count,
            ws.entities,
            ws.recent_events,
        )
        if workspace_key == getattr(self, "_last_workspace_key", None):
            return
        self._last_workspace_key = workspace_key
        self._entities = ws.entities
        self._stats_label.configure(
            text=(
                f"{ws.entity_count} entities · "
                f"{ws.relationship_count} links · "
                f"{ws.event_count} events"
            )
        )
        clear_children(self._canvas_host)

        if not ws.entities and not ws.recent_events:
            self._render_empty_state()
            return

        if ws.recent_events:
            self._render_activity(ws.recent_events)

        grouped: dict[str, list] = {key: [] for key, _ in _GROUP_ORDER}
        for entity in ws.entities:
            bucket = grouped.get(entity.entity_type)
            if bucket is not None:
                bucket.append(entity)

        for type_key, label in _GROUP_ORDER:
            group = grouped.get(type_key, [])
            if group:
                self._render_entity_group(
                    self._canvas_host,
                    label=label,
                    entity_type=type_key,
                    entities=group,
                )

        if not ws.entities and ws.recent_events:
            ctk.CTkLabel(
                self._canvas_host,
                text="No entities yet — create a workspace to get started.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(pady=16)
