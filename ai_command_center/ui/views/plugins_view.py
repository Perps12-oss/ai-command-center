"""Plugin catalog panel — reads plugin.catalog from EventBus (Phase 5B)."""



from __future__ import annotations



import customtkinter as ctk



from ai_command_center.ui.components.floating_ui import FLOAT_GAP, FLOAT_PAD, floating_scroll, pack_floating

from ai_command_center.ui.components.glass_card import GlassCard

from ai_command_center.ui.layer.layer_stack import PageLayerStack

from ai_command_center.ui.theme import tokens as T





class PluginsView(PageLayerStack):

    def __init__(self, master, *, on_toggle) -> None:

        super().__init__(master, "plugins")

        self._on_toggle = on_toggle

        self._rows: dict[str, ctk.CTkFrame] = {}



        header_card = GlassCard(self.ui_layer)

        pack_floating(header_card, first=True)

        ctk.CTkLabel(

            header_card,

            text="Plugins",

            font=T.FONT_TITLE,

            text_color=T.TEXT_HEADING,

        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 4))

        ctk.CTkLabel(

            header_card,

            text="Declarative manifests under plugins/manifests/. Core plugins register via EventBus only.",

            font=T.FONT_SMALL,

            text_color=T.TEXT_MUTED,

            wraplength=640,

            justify="left",

        ).pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))



        self._list = floating_scroll(self.ui_layer, height=360)

        self._list.pack(fill="x", expand=False, padx=FLOAT_PAD, pady=(0, FLOAT_GAP))



        self._status = ctk.CTkLabel(

            self.ui_layer,

            text="Loading catalog…",

            font=T.FONT_SMALL,

            text_color=T.TEXT_MUTED,

        )

        self._status.pack(anchor="w", padx=FLOAT_PAD, pady=(0, FLOAT_PAD))



    def show_catalog(self, plugins: list[dict]) -> None:

        for child in self._list.winfo_children():

            child.destroy()

        self._rows.clear()



        if not plugins:

            self._status.configure(text="No plugins found in plugins/manifests/")

            return



        for plugin in plugins:

            self._add_row(plugin)



        enabled = sum(1 for p in plugins if p.get("enabled"))

        self._status.configure(text=f"{len(plugins)} plugin(s) — {enabled} enabled")



    def show_error(self, message: str) -> None:

        self._status.configure(text=message, text_color=T.STATUS_ERROR)



    def _add_row(self, plugin: dict) -> None:

        plugin_id = str(plugin.get("id", ""))

        row = GlassCard(self._list, with_shadow=False)

        row.pack(fill="x", padx=4, pady=6)



        header = ctk.CTkFrame(row, fg_color="transparent")

        header.pack(fill="x", padx=12, pady=(10, 4))



        ctk.CTkLabel(

            header,

            text=str(plugin.get("name", plugin_id)),

            font=T.FONT_HEADER,

            text_color=T.TEXT_PRIMARY,

        ).pack(side="left")



        kind = str(plugin.get("kind", "extension"))

        ctk.CTkLabel(

            header,

            text=kind,

            font=T.FONT_SMALL,

            text_color=T.TEXT_MUTED,

        ).pack(side="right")



        ctk.CTkLabel(

            row,

            text=str(plugin.get("description", "")),

            font=T.FONT_SMALL,

            text_color=T.TEXT_SECONDARY,

            wraplength=560,

            justify="left",

        ).pack(anchor="w", padx=12, pady=(0, 4))



        topics = plugin.get("bus_topics") or []

        if topics:

            ctk.CTkLabel(

                row,

                text="Topics: " + ", ".join(str(t) for t in topics),

                font=T.FONT_SMALL,

                text_color=T.TEXT_MUTED,

                wraplength=560,

                justify="left",

            ).pack(anchor="w", padx=12, pady=(0, 8))



        enabled = bool(plugin.get("enabled", True))

        if kind == "core":

            ctk.CTkLabel(

                row,

                text="Core — always enabled",

                font=T.FONT_SMALL,

                text_color=T.STATUS_READY,

            ).pack(anchor="w", padx=12, pady=(0, 10))

        else:

            label = "Disable" if enabled else "Enable"

            ctk.CTkButton(

                row,

                text=label,

                width=90,

                height=28,

                font=T.FONT_SMALL,

                command=lambda pid=plugin_id, en=enabled: self._on_toggle(pid, not en),

            ).pack(anchor="w", padx=12, pady=(0, 10))



        self._rows[plugin_id] = row

