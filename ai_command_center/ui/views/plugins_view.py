"""Plugin catalog panel — reads plugin.catalog from EventBus (Phase 5B)."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class PluginsView(ctk.CTkFrame):
    def __init__(self, master, *, on_toggle) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_toggle = on_toggle
        self._rows: dict[str, ctk.CTkFrame] = {}

        ctk.CTkLabel(
            self,
            text="Plugins",
            font=T.FONT_TITLE,
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 8))

        ctk.CTkLabel(
            self,
            text="Declarative manifests under plugins/manifests/. Core plugins register via EventBus only.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            wraplength=640,
            justify="left",
        ).pack(anchor="w", padx=T.PAD, pady=(0, 12))

        self._status = ctk.CTkLabel(
            self,
            text="Loading catalog…",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._status.pack(anchor="w", padx=T.PAD, pady=(0, 4))

        self._list = ctk.CTkScrollableFrame(self, fg_color=T.BG_GLASS, corner_radius=T.CORNER_RADIUS)
        self._list.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

    def load_from_appstate(self, snap) -> None:
        """Render plugin catalog from AppState projection."""
        plugins = [
            {
                "id": item.plugin_id,
                "name": item.name,
                "description": item.description,
                "kind": item.kind,
                "enabled": item.enabled,
                "error": item.error,
                "pending_restart": item.pending_restart,
            }
            for item in snap.plugin_catalog
        ]
        self.show_catalog(plugins)

    def show_catalog(self, plugins: list[dict]) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        self._rows.clear()

        if not plugins:
            self._status.configure(text="No plugins found in plugins/manifests/")
            return

        core = [p for p in plugins if str(p.get("kind", "extension")) == "core"]
        ext = [p for p in plugins if str(p.get("kind", "extension")) != "core"]
        if core:
            self._add_section("Core plugins")
            for plugin in core:
                self._add_row(plugin)
        if ext:
            self._add_section("Extensions")
            for plugin in ext:
                self._add_row(plugin)

        enabled = sum(1 for p in plugins if p.get("enabled"))
        self._status.configure(text=f"{len(plugins)} plugin(s) — {enabled} enabled")

    def _add_section(self, label: str) -> None:
        ctk.CTkLabel(
            self._list,
            text=label.upper(),
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 4))

    def show_error(self, message: str) -> None:
        self._status.configure(text=message, text_color=T.STATUS_ERROR)

    def _add_row(self, plugin: dict) -> None:
        from ai_command_center.ui.components.glass_card import GlassCard

        plugin_id = str(plugin.get("id", ""))
        kind = str(plugin.get("kind", "extension"))
        enabled = bool(plugin.get("enabled", True))
        error = str(plugin.get("error", ""))
        pending = bool(plugin.get("pending_restart", False))

        card = GlassCard(self._list)
        card.pack(fill="x", padx=8, pady=6)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(10, 10))

        header = ctk.CTkFrame(row, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            header,
            text=str(plugin.get("name", plugin_id)),
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        status_color = T.STATUS_ERROR if error else T.STATUS_READY if enabled else T.STATUS_BUSY
        status_text = "error" if error else "enabled" if enabled else "disabled"
        ctk.CTkLabel(
            header,
            text=status_text,
            font=T.FONT_SMALL,
            text_color=status_color,
        ).pack(side="right")

        ctk.CTkLabel(
            row,
            text=str(plugin.get("description", "")),
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(0, 4))

        topics = plugin.get("bus_topics") or []
        if topics:
            ctk.CTkLabel(
                row,
                text="Topics: " + ", ".join(str(t) for t in topics),
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                wraplength=560,
                justify="left",
            ).pack(anchor="w", pady=(0, 4))

        if error:
            ctk.CTkLabel(
                row,
                text=f"Error: {error}",
                font=T.FONT_SMALL,
                text_color=T.STATUS_ERROR,
                wraplength=560,
                justify="left",
            ).pack(anchor="w", pady=(0, 4))

        footer = ctk.CTkFrame(row, fg_color="transparent")
        footer.pack(fill="x", pady=(4, 0))
        if kind == "core":
            ctk.CTkLabel(
                footer,
                text="Core — always enabled",
                font=T.FONT_SMALL,
                text_color=T.STATUS_READY,
            ).pack(side="left")
        else:
            label = "Disable" if enabled else "Enable"
            ctk.CTkButton(
                footer,
                text=label,
                width=90,
                height=28,
                font=T.FONT_SMALL,
                fg_color=T.ACCENT_DEFAULT if not enabled else T.BG_GLASS,
                hover_color=T.ACCENT_HOVER if not enabled else T.BG_GLASS_BORDER,
                text_color="white" if not enabled else T.TEXT_PRIMARY,
                command=lambda pid=plugin_id, en=enabled: self._mark_pending(pid, not en),
            ).pack(side="left")

        if pending:
            ctk.CTkLabel(
                footer,
                text="Restart required",
                font=T.FONT_SMALL,
                text_color=T.STATUS_BUSY,
            ).pack(side="left", padx=(12, 0))

        self._rows[plugin_id] = card

    def _mark_pending(self, plugin_id: str, enabled: bool) -> None:
        self._on_toggle(plugin_id, enabled)
        card = self._rows.get(plugin_id)
        if card is not None:
            footer = None
            for child in card.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for sub in child.winfo_children():
                        if isinstance(sub, ctk.CTkFrame):
                            footer = sub
                            break
            if footer is not None:
                for child in footer.winfo_children():
                    if isinstance(child, ctk.CTkLabel) and "Restart" in str(child.cget("text")):
                        return
                ctk.CTkLabel(
                    footer,
                    text="Restart required",
                    font=T.FONT_SMALL,
                    text_color=T.STATUS_BUSY,
                ).pack(side="left", padx=(12, 0))
