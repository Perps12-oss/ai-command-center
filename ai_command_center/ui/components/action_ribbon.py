"""Slim action ribbon — pill buttons with light border + cyan hover."""



from __future__ import annotations



import customtkinter as ctk



from ai_command_center.ui.components.glass_card import GlassCard

from ai_command_center.ui.theme import tokens as T





class ActionRibbon(GlassCard):

    def __init__(

        self,

        master,

        *,

        on_new_session=None,

        on_scan=None,

        on_clear_logs=None,

        **kwargs,

    ) -> None:

        super().__init__(master, with_shadow=False, corner_radius=T.CARD_RADIUS, **kwargs)

        self._on_new_session = on_new_session

        self._on_scan = on_scan

        self._on_clear_logs = on_clear_logs



        inner = ctk.CTkFrame(self, fg_color="transparent")

        inner.pack(fill="both", expand=True, padx=T.PAD, pady=8)



        ctk.CTkLabel(

            inner,

            text="◇",

            font=(T.FONT_FAMILY, 20, "bold"),

            text_color=T.HERO_CYAN,

        ).pack(side="left", padx=(0, 12))



        ctk.CTkLabel(

            inner,

            text="Command Console",

            font=T.FONT_HEADER,

            text_color=T.TEXT_HEADING,

        ).pack(side="left", padx=(0, 24))



        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")

        btn_frame.pack(side="left", fill="y")



        for label, cmd in (

            ("New Session", self._new_session),

            ("Scan System", self._scan),

            ("Clear Logs", self._clear_logs),

        ):

            self._pill(btn_frame, label, cmd).pack(side="left", padx=4)



        spacer = ctk.CTkFrame(inner, fg_color="transparent")

        spacer.pack(side="left", expand=True, fill="x")



    def _pill(self, master, text: str, command) -> ctk.CTkButton:

        btn = ctk.CTkButton(

            master,

            text=text,

            height=32,

            font=T.FONT_SMALL,

            fg_color=T.RIBBON_PILL_BG,

            hover_color=T.LIGHT_GLASS,

            border_width=0,

            border_color=T.RIBBON_PILL_BG,

            text_color=T.TEXT_SECONDARY,

            command=command,

        )

        btn.bind("<Enter>", lambda _e: btn.configure(fg_color=T.GLASS_BORDER, text_color=T.TEXT_HEADING))

        btn.bind("<Leave>", lambda _e: btn.configure(fg_color=T.RIBBON_PILL_BG, text_color=T.TEXT_SECONDARY))

        return btn



    def _new_session(self) -> None:

        if self._on_new_session:

            self._on_new_session()



    def _scan(self) -> None:

        if self._on_scan:

            self._on_scan()



    def _clear_logs(self) -> None:

        if self._on_clear_logs:

            self._on_clear_logs()



    def set_live(self, cpu: float, ram: float, model_load: float, *, glow: float = 0.3) -> None:

        pass


