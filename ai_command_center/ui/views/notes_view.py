"""Obsidian notes — SPLIT_3PANE (search / results / preview)."""



from __future__ import annotations



import customtkinter as ctk



from ai_command_center.ui.components.glass_card import GlassCard

from ai_command_center.ui.components.floating_ui import FLOAT_GAP, FLOAT_PAD, floating_scroll, pack_floating

from ai_command_center.ui.components.page_header import PageHeader

from ai_command_center.ui.layer.layer_stack import PageLayerStack

from ai_command_center.ui.theme import tokens as T



_SEARCH_W = 240

_RESULTS_W = 320





class NotesView(PageLayerStack):

    def __init__(self, master, on_select, **kwargs) -> None:

        super().__init__(master, "notes", **kwargs)

        self._on_select = on_select

        self._preview_body = ""



        header_card = GlassCard(self.ui_layer)

        pack_floating(header_card, first=True)

        PageHeader(

            header_card,

            title="Notes",

            subtitle="Vault search and preview",

        ).pack(fill="x", padx=T.PAD, pady=T.PAD)



        panes = ctk.CTkFrame(self.ui_layer, fg_color="transparent")

        panes.pack(fill="x", expand=False, padx=FLOAT_PAD, pady=(0, FLOAT_GAP))

        panes.columnconfigure(2, weight=1)

        panes.rowconfigure(0, weight=1)



        search_card = GlassCard(panes)

        search_card.grid(row=0, column=0, sticky="nsew", padx=(0, T.GAP // 2))

        search_card.configure(width=_SEARCH_W)

        search_card.pack_propagate(False)



        ctk.CTkLabel(

            search_card,

            text="Search",

            font=T.FONT_HEADER,

            text_color=T.TEXT_PRIMARY,

        ).pack(anchor="w", padx=12, pady=(12, 4))

        ctk.CTkLabel(

            search_card,

            text="Use command box:\nnote: your query",

            font=T.FONT_SMALL,

            text_color=T.TEXT_MUTED,

            justify="left",

        ).pack(anchor="w", padx=12, pady=4)

        self._search_status = ctk.CTkLabel(

            search_card,

            text="Ready",

            font=T.FONT_SMALL,

            text_color=T.TEXT_SECONDARY,

            wraplength=_SEARCH_W - 24,

            justify="left",

        )

        self._search_status.pack(anchor="w", padx=12, pady=8)



        results_card = GlassCard(panes)

        results_card.grid(row=0, column=1, sticky="nsew", padx=(T.GAP // 2, T.GAP // 2))

        results_card.configure(width=_RESULTS_W)

        results_card.pack_propagate(False)



        self._status = ctk.CTkLabel(

            results_card,

            text="No results yet",

            font=T.FONT_SMALL,

            text_color=T.TEXT_MUTED,

            wraplength=_RESULTS_W - 24,

            justify="left",

        )

        self._status.pack(fill="x", padx=12, pady=(12, 4))



        self._scroll = floating_scroll(results_card, height=320)

        self._scroll.pack(fill="x", expand=False, padx=12, pady=(0, 12))



        preview_card = GlassCard(panes)

        preview_card.grid(row=0, column=2, sticky="nsew", padx=(T.GAP // 2, 0))



        ctk.CTkLabel(

            preview_card,

            text="Preview",

            font=T.FONT_HEADER,

            text_color=T.TEXT_PRIMARY,

        ).pack(anchor="w", padx=12, pady=(12, 4))



        self._selected = ctk.CTkLabel(

            preview_card,

            text="Select a note to preview",

            font=T.FONT_SMALL,

            text_color=T.STATUS_READY,

            anchor="w",

            justify="left",

        )

        self._selected.pack(fill="x", padx=12, pady=(0, 4))



        self._preview = ctk.CTkTextbox(

            preview_card,

            font=T.FONT_BODY,

            fg_color=T.LIGHT_GLASS,

            text_color=T.TEXT_SECONDARY,

            wrap="word",

            height=280,

        )

        self._preview.pack(fill="x", expand=False, padx=12, pady=(0, 12))

        self._preview.configure(state="disabled")



    def show_results(self, query: str, results: list[dict]) -> None:

        for child in self._scroll.winfo_children():

            child.destroy()



        self._search_status.configure(text=f'Query: "{query}"')



        if not results:

            self._status.configure(

                text=f'No results for "{query}"',

                text_color=T.TEXT_MUTED,

            )

            return



        self._status.configure(

            text=f"{len(results)} result(s)",

            text_color=T.TEXT_SECONDARY,

        )

        for item in results:

            path = str(item.get("path", ""))

            title = str(item.get("title", path))

            snippet = str(item.get("snippet", ""))

            row = ctk.CTkFrame(self._scroll, fg_color=T.BG_GLASS, corner_radius=8)

            row.pack(fill="x", pady=4)



            ctk.CTkLabel(

                row,

                text=title,

                font=T.FONT_HEADER,

                text_color=T.TEXT_PRIMARY,

                anchor="w",

            ).pack(fill="x", padx=8, pady=(6, 0))



            if snippet:

                ctk.CTkLabel(

                    row,

                    text=snippet[:80],

                    font=T.FONT_SMALL,

                    text_color=T.TEXT_MUTED,

                    anchor="w",

                    wraplength=_RESULTS_W - 40,

                ).pack(fill="x", padx=8, pady=2)



            btn_row = ctk.CTkFrame(row, fg_color="transparent")

            btn_row.pack(fill="x", padx=8, pady=(0, 6))

            ctk.CTkButton(

                btn_row,

                text="Preview",

                width=70,

                height=24,

                font=T.FONT_SMALL,

                command=lambda p=path, t=title, s=snippet: self._show_preview(p, t, s),

            ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(

                btn_row,

                text="Use in chat",

                width=90,

                height=24,

                font=T.FONT_SMALL,

                command=lambda p=path: self._on_select(p),

            ).pack(side="left")



    def _show_preview(self, path: str, title: str, snippet: str) -> None:

        self._selected.configure(text=f"{title} ({path})")

        body = snippet or "(No preview body — select Use in chat to load full note)"

        self._preview.configure(state="normal")

        self._preview.delete("1.0", "end")

        self._preview.insert("1.0", body)

        self._preview.configure(state="disabled")



    def show_selected(self, path: str, title: str) -> None:

        self._selected.configure(text=f"Injecting into next chat: {title} ({path})")



    def show_error(self, message: str) -> None:

        self._status.configure(text=message, text_color=T.STATUS_ERROR)

        self._search_status.configure(text="Error", text_color=T.STATUS_ERROR)



    def show_created(self, path: str, title: str) -> None:

        self._status.configure(

            text=f'Created "{title}" at {path}',

            text_color=T.STATUS_READY,

        )

