"""Workspace canvas — entity grid projected from AppState."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.widget_utils import clear_children

_TYPE_ICON = {
    "workspace": "◈",
    "card": "▢",
    "resource": "🔗",
}


class _EntityTile(GlassCard):
    def __init__(
        self,
        master,
        *,
        title: str,
        entity_type: str,
        subtitle: str,
        on_launch: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
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
        if on_launch is not None:
            ctk.CTkButton(
                self,
                text="Launch",
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.ACCENT_DEFAULT,
                hover_color=T.ACCENT_HOVER,
                command=on_launch,
            ).pack(anchor="w", padx=12, pady=(8, 10))
        else:
            ctk.CTkFrame(self, fg_color="transparent", height=8).pack()


class WorkspaceView(ctk.CTkFrame):
    """Primary workspace surface — renders Workspace OS entities from AppState."""

    def __init__(
        self,
        master,
        *,
        on_launch: Callable[[dict], None],
        on_command: Callable[[str], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_launch = on_launch
        self._on_command = on_command
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
            command=lambda: self._on_command("workspace: new"),
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

        self._empty_label = ctk.CTkLabel(
            self._canvas_host,
            text="No entities yet.\nUse + Workspace or Ctrl+Shift+W to create cards and resources.",
            font=T.FONT_BODY,
            text_color=T.TEXT_MUTED,
            justify="center",
        )

    def load_from_appstate(self, snap) -> None:
        ws = snap.workspace_os
        self._stats_label.configure(
            text=(
                f"{ws.entity_count} entities · "
                f"{ws.relationship_count} links · "
                f"{ws.event_count} events"
            )
        )
        clear_children(self._canvas_host)
        entities = list(ws.entities)
        if not entities:
            self._empty_label = ctk.CTkLabel(
                self._canvas_host,
                text="No entities yet.\nUse + Workspace or Ctrl+Shift+W to create cards and resources.",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
                justify="center",
            )
            self._empty_label.pack(pady=40)
            return

        grid = ctk.CTkFrame(self._canvas_host, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        columns = 3
        for index, entity in enumerate(entities):
            meta = dict(entity.metadata)
            subtitle = meta.get("description") or meta.get("url") or meta.get("path") or meta.get("command") or ""
            resource_type = meta.get("resource_type")
            value = meta.get("url") or meta.get("path") or meta.get("command") or ""
            launch: Callable[[], None] | None = None
            if entity.entity_type == "resource" and resource_type and value:
                payload = {
                    "resource_id": entity.entity_id,
                    "resource_type": resource_type,
                    "value": value,
                }

                def _launch_handler(p: dict = payload) -> None:
                    self._on_launch(p)

                launch = _launch_handler
            row, col = divmod(index, columns)
            tile = _EntityTile(
                grid,
                title=entity.title or entity.entity_id,
                entity_type=entity.entity_type,
                subtitle=str(subtitle)[:120],
                on_launch=launch,
            )
            tile.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1)
