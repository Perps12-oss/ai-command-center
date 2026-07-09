"""Chat composer v2 — toolbar, model selector, token footer."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.stream_renderer import CLR_META

_PILL_MAX_LINES = 4
_LINE_H = 22
_PLACEHOLDER = "Type your message…"

PROMPT_TEMPLATES: list[tuple[str, str, str]] = [
    ("Summarise", "Summarise the following: ", "Condense into key points"),
    ("Explain simply", "Explain this like I'm 5: ", "Plain-language explanation"),
    ("Bullet points", "Give me bullet points for: ", "List format"),
    ("Pros & cons", "List the pros and cons of: ", "Balanced analysis"),
    ("Action items", "Extract action items from: ", "Task extraction"),
    ("Write email", "Write a professional email about: ", "Email draft"),
    ("Debug help", "Help me debug this issue: ", "Code / logic debugging"),
    ("Compare", "Compare and contrast: ", "Side-by-side comparison"),
]

CLR_HINT = "#3A3F5C"


class TemplatesOverlay(ctk.CTkFrame):
    """Floating chip grid of prompt templates."""

    def __init__(self, master, on_select: Callable[[str], None]) -> None:
        super().__init__(
            master,
            fg_color=T.SURFACE_PRIMARY,
            border_color=T.BORDER_SUBTLE,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
        )
        self._on_select = on_select
        self._visible = False
        ctk.CTkLabel(
            self,
            text="PROMPT TEMPLATES",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 4))
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=(0, 8))
        for col in range(2):
            grid.columnconfigure(col, weight=1)
        for i, (label, prefix, hint) in enumerate(PROMPT_TEMPLATES):
            chip = ctk.CTkFrame(
                grid,
                fg_color=T.SURFACE_ELEVATED,
                border_color=T.BORDER_SUBTLE,
                border_width=1,
                corner_radius=T.SMALL_RADIUS,
            )
            chip.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=2)
            ctk.CTkLabel(
                chip, text=label, font=T.FONT_SMALL, text_color=T.TEXT_PRIMARY, anchor="w"
            ).pack(side="left", padx=(8, 4), pady=4)
            ctk.CTkLabel(
                chip, text=hint, font=(T.FONT_FAMILY, 9), text_color=T.TEXT_MUTED, anchor="e"
            ).pack(side="right", padx=(0, 8), pady=4)
            chip.bind("<Button-1>", lambda _e, p=prefix: self._pick(p))
            for w in chip.winfo_children():
                w.bind("<Button-1>", lambda _e, p=prefix: self._pick(p))

    def _pick(self, prefix: str) -> None:
        self._on_select(prefix)
        self.hide()

    def show_above(self, anchor_widget) -> None:
        if self._visible:
            self.hide()
            return
        self._visible = True
        self.place(in_=anchor_widget, relx=0.0, rely=0.0, anchor="sw", bordermode="outside")
        self.lift()

    def hide(self) -> None:
        self._visible = False
        self.place_forget()


class InputPill(ctk.CTkFrame):
    """Chat composer v2 — 96px pinned area with toolbar and model selector."""

    def __init__(
        self,
        master,
        on_send: Callable[[str], None] | None,
        on_stop: Callable[[], None],
        *,
        on_model_change: Callable[[str], None] | None = None,
        on_toolbar_stub: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.SURFACE_PRIMARY,
            corner_radius=0,
            height=T.COMPOSER_HEIGHT + 28,
        )
        self.pack_propagate(False)
        self._on_send = on_send
        self._on_stop = on_stop
        self._on_model_change = on_model_change
        self._on_toolbar_stub = on_toolbar_stub
        self._streaming = False
        self._ph_active = True
        self._current_model = "llama3.2:3b"

        pill = ctk.CTkFrame(
            self,
            fg_color=T.SURFACE_ELEVATED,
            corner_radius=T.INPUT_RADIUS,
            border_color=T.BORDER_SUBTLE,
            border_width=1,
        )
        pill.pack(fill="x", padx=16, pady=(8, 4))

        self._tb = ctk.CTkTextbox(
            pill,
            font=T.FONT_BODY,
            fg_color="transparent",
            text_color=T.TEXT_PRIMARY,
            wrap="word",
            activate_scrollbars=False,
            height=36,
            border_width=0,
            corner_radius=0,
        )
        self._tb.pack(fill="x", padx=12, pady=(10, 4))
        self._tb.insert("1.0", _PLACEHOLDER)
        self._tb.configure(text_color=CLR_META)
        self._tb.bind("<FocusIn>", self._focus_in)
        self._tb.bind("<FocusOut>", self._focus_out)
        self._tb.bind("<Return>", self._on_enter)
        self._tb.bind("<KeyRelease>", self._grow)

        toolbar = ctk.CTkFrame(pill, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(0, 8))

        btn_style = dict(
            width=28,
            height=28,
            font=(T.FONT_FAMILY, 12),
            fg_color="transparent",
            hover_color=T.SURFACE_SECONDARY,
            text_color=T.TEXT_MUTED,
            corner_radius=6,
        )

        self._tmpl_btn = ctk.CTkButton(
            toolbar, text="+", command=self._toggle_templates, **btn_style
        )
        self._tmpl_btn.pack(side="left", padx=2)
        self._templates_overlay: TemplatesOverlay | None = None

        for icon, hint in (("@", "mention"), ("</>", "code"), ("📎", "attach")):
            ctk.CTkButton(
                toolbar,
                text=icon,
                command=lambda h=hint: self._stub(h),
                **btn_style,
            ).pack(side="left", padx=2)

        self._model_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["llama3.2:3b"],
            command=self._on_model_pick,
            width=120,
            height=28,
            font=(T.FONT_FAMILY, 10),
            fg_color=T.SURFACE_SECONDARY,
            button_color=T.ACCENT_PURPLE,
            button_hover_color=T.ACCENT_HOVER,
            dropdown_fg_color=T.SURFACE_ELEVATED,
            text_color=T.TEXT_PRIMARY,
        )
        self._model_menu.pack(side="right", padx=(4, 4))
        self._model_menu.set("llama3.2:3b")

        self._btn = ctk.CTkButton(
            toolbar,
            text="➤",
            width=32,
            height=28,
            font=(T.FONT_FAMILY, 13, "bold"),
            fg_color=T.ACCENT_PURPLE,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=8,
            command=self._action,
        )
        self._btn.pack(side="right", padx=(0, 2))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(
            footer,
            text="Press Enter to send · Shift+Enter new line · Ctrl+K palette · Alt+Space",
            font=(T.FONT_FAMILY, 9),
            text_color=CLR_HINT,
        ).pack(side="left")

        self._context_lbl = ctk.CTkLabel(
            footer,
            text="Tokens: —",
            font=(T.FONT_FAMILY, 9),
            text_color=CLR_META,
        )
        self._context_lbl.pack(side="right")

        self._status = ctk.CTkLabel(
            footer,
            text="",
            font=(T.FONT_FAMILY, 10),
            text_color=CLR_META,
        )
        self._status.pack(side="right", padx=(0, 12))

    def _stub(self, hint: str) -> None:
        if self._on_toolbar_stub:
            self._on_toolbar_stub(hint)

    def _on_model_pick(self, model: str) -> None:
        self._current_model = model
        if self._on_model_change:
            self._on_model_change(model)

    def set_model(self, model: str) -> None:
        self._current_model = model
        try:
            self._model_menu.set(model)
        except Exception:
            pass

    def set_models(self, models: list[str], current: str = "") -> None:
        if models:
            self._model_menu.configure(values=models)
            pick = current or self._current_model
            if pick in models:
                self._model_menu.set(pick)

    def update_context_footer(self, sources: list[str], tokens: int) -> None:
        if tokens:
            self._context_lbl.configure(text=f"Tokens: ~{tokens}")
        else:
            self._context_lbl.configure(text="Tokens: —")

    def _focus_in(self, _=None) -> None:
        if self._ph_active:
            self._tb.delete("1.0", "end")
            self._tb.configure(text_color=T.TEXT_PRIMARY)
            self._ph_active = False

    def _focus_out(self, _=None) -> None:
        if not self._tb.get("1.0", "end-1c").strip():
            self._tb.insert("1.0", _PLACEHOLDER)
            self._tb.configure(text_color=CLR_META)
            self._ph_active = True
            self._tb.configure(height=36)

    def _grow(self, _=None) -> None:
        if self._ph_active:
            return
        lines = int(self._tb.index("end-1c").split(".")[0])
        h = max(36, min(lines * _LINE_H, _PILL_MAX_LINES * _LINE_H))
        self._tb.configure(height=h)

    def _on_enter(self, event) -> str:
        if event.state & 0x1:
            return ""
        self._submit()
        return "break"

    def _submit(self) -> None:
        if self._ph_active:
            return
        text = self._tb.get("1.0", "end-1c").strip()
        if not text:
            return
        if self._on_send:
            self._tb.delete("1.0", "end")
            self._tb.configure(height=36)
            self._focus_out()
            self._on_send(text)

    def _action(self) -> None:
        if self._streaming:
            self._on_stop()
        else:
            self._submit()

    def set_streaming(self, active: bool) -> None:
        self._streaming = active
        if active:
            self._btn.configure(text="■", fg_color=T.ERROR_RED, hover_color="#8B0000")
            self._status.configure(text="Generating…", text_color=T.STATUS_BUSY)
        else:
            self._btn.configure(text="➤", fg_color=T.ACCENT_PURPLE, hover_color=T.ACCENT_HOVER)
            self._status.configure(text="")

    def set_status(self, text: str, color: str = "") -> None:
        self._status.configure(text=text, text_color=color or CLR_META)

    def focus_input(self) -> None:
        self._tb.focus_set()
        self._focus_in()

    def set_templates_overlay(self, overlay: TemplatesOverlay) -> None:
        self._templates_overlay = overlay

    def _toggle_templates(self) -> None:
        if self._templates_overlay:
            self._templates_overlay.show_above(self._tmpl_btn)

    def insert_template(self, prefix: str) -> None:
        self._focus_in()
        current = self._tb.get("1.0", "end-1c")
        self._tb.delete("1.0", "end")
        self._tb.insert("1.0", prefix + current)
        self._tb.mark_set("insert", "end")
        self._tb.focus_set()
        self._grow()
