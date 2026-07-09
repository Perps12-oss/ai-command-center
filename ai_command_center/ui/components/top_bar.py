"""Top bar — v2 workspace strip with model dropdown and command palette."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class TopBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_settings,
        on_close,
        *,
        on_palette: Callable[[], None] | None = None,
        on_model_change: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            height=T.TOP_BAR_HEIGHT,
            fg_color=T.SURFACE_PRIMARY,
            border_width=0,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._on_palette = on_palette
        self._on_model_change = on_model_change
        self._models: list[str] = []
        self._current_model = "llama3.2:3b"

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=T.PAD, pady=12)

        ctk.CTkLabel(
            left,
            text="◇ AI Command Center",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        ).pack(side="left")

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.pack(side="left", expand=True)

        self._model_menu = ctk.CTkOptionMenu(
            center,
            values=["llama3.2:3b"],
            command=self._on_model_selected,
            width=180,
            height=32,
            font=T.FONT_SMALL,
            fg_color=T.SURFACE_ELEVATED,
            button_color=T.ACCENT_PURPLE,
            button_hover_color=T.ACCENT_HOVER,
            dropdown_fg_color=T.SURFACE_SECONDARY,
            dropdown_hover_color=T.SURFACE_ELEVATED,
            text_color=T.TEXT_PRIMARY,
        )
        self._model_menu.pack(anchor="center", pady=4)
        self._model_menu.set("llama3.2:3b")

        self._status_frame = ctk.CTkFrame(center, fg_color="transparent")
        self._status_frame.pack(anchor="center")
        self._status_dot = ctk.CTkLabel(
            self._status_frame,
            text="●",
            font=(T.FONT_FAMILY, 10),
            text_color=T.SUCCESS_GREEN,
            width=14,
        )
        self._status_dot.pack(side="left")
        self._status_lbl = ctk.CTkLabel(
            self._status_frame,
            text="Connected",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
        )
        self._status_lbl.pack(side="left", padx=(2, 0))

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=T.PAD, pady=12)

        if on_palette:
            ctk.CTkButton(
                right,
                text="⌘K",
                width=44,
                height=32,
                font=(T.FONT_FAMILY, 11, "bold"),
                fg_color=T.SURFACE_ELEVATED,
                hover_color=T.SURFACE_SECONDARY,
                text_color=T.TEXT_SECONDARY,
                corner_radius=T.BUTTON_RADIUS,
                command=on_palette,
            ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            right,
            text="Alt+Space",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right,
            text="⚙",
            width=36,
            height=36,
            font=T.FONT_BODY,
            fg_color=T.SURFACE_ELEVATED,
            hover_color=T.SURFACE_SECONDARY,
            border_width=0,
            corner_radius=T.BUTTON_RADIUS,
            command=on_settings,
        ).pack(side="left", padx=4)

        self._avatar = ctk.CTkLabel(
            right,
            text="U",
            width=36,
            height=36,
            font=(T.FONT_FAMILY, 14, "bold"),
            fg_color=T.ACCENT_PURPLE,
            text_color="#FFFFFF",
            corner_radius=18,
        )
        self._avatar.pack(side="left", padx=(4, 4))

        ctk.CTkButton(
            right,
            text="✕",
            width=36,
            height=36,
            font=T.FONT_BODY,
            fg_color=T.SURFACE_ELEVATED,
            hover_color=T.STATUS_ERROR,
            border_width=0,
            corner_radius=T.BUTTON_RADIUS,
            command=on_close,
        ).pack(side="left", padx=4)

    def _on_model_selected(self, model: str) -> None:
        self._current_model = model
        if self._on_model_change:
            self._on_model_change(model)

    def set_models(self, models: list[str], current: str = "") -> None:
        if not models:
            return
        self._models = list(models)
        self._model_menu.configure(values=self._models)
        pick = current or self._current_model
        if pick in self._models:
            self._model_menu.set(pick)
            self._current_model = pick
        elif self._models:
            self._model_menu.set(self._models[0])
            self._current_model = self._models[0]

    def update_status(self, phase: str, model: str) -> None:
        if model:
            self._current_model = model
            if model in self._models or not self._models:
                try:
                    self._model_menu.set(model)
                except Exception:
                    pass

    def update_llm_status(
        self,
        *,
        provider: str,
        phase: str,
        model: str,
        ollama_online: bool,
        openai_online: bool,
        openai_configured: bool,
    ) -> None:
        """Reflect active provider, model, and connection health in the top bar."""
        self.update_status(phase, model)

        if phase in {"starting", "busy"}:
            self._set_connection("Busy", T.STATUS_BUSY)
            return
        if phase in {"error", "stopped"}:
            self._set_connection("Error", T.STATUS_ERROR)
            return

        if provider == "openai":
            if not openai_configured:
                self._set_connection("No API key", T.TEXT_MUTED)
            elif openai_online:
                self._set_connection("Connected", T.SUCCESS_GREEN)
            else:
                self._set_connection("Offline", T.TEXT_MUTED)
            return

        if ollama_online:
            self._set_connection("Connected", T.SUCCESS_GREEN)
        else:
            self._set_connection("Offline", T.TEXT_MUTED)

    def _set_connection(self, label: str, color: str) -> None:
        self._status_dot.configure(text_color=color)
        self._status_lbl.configure(text=label)

    def set_ollama_online(self, online: bool) -> None:
        """Backward-compatible hook for legacy Ollama-only updates."""
        if online:
            self._set_connection("Connected", T.SUCCESS_GREEN)
        else:
            self._set_connection("Offline", T.TEXT_MUTED)
