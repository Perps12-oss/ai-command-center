"""Top bar — glass strip continuous with sidebar."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.providers.defaults import provider_display_name
from ai_command_center.ui.components.status_pill import StatusPill
from ai_command_center.ui.design_system import theme_v2 as T


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_settings, on_close, **kwargs) -> None:
        super().__init__(
            master,
            height=T.TOP_BAR_HEIGHT,
            fg_color="transparent",
            border_width=0,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=T.PAD, pady=10)

        ctk.CTkLabel(
            left,
            text="◇ AI Command Center",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        ).pack(side="left")

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.pack(side="left", expand=True, padx=T.PAD)

        self._model_label = ctk.CTkLabel(
            center,
            text="llama3.2:3b",
            font=T.FONT_HEADER,
            text_color=T.TEXT_HEADING,
        )
        self._model_label.pack(anchor="center")

        self._provider_label = ctk.CTkLabel(
            center,
            text="Ollama (local)",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        )
        self._provider_label.pack(anchor="center")

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=T.PAD, pady=10)

        self._pill = StatusPill(right, "Connected", state="ready")
        self._pill.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            right,
            text="Alt+Space",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right,
            text="⚙",
            width=36,
            height=36,
            font=T.FONT_BODY,
            fg_color=T.GLASS_BG,
            hover_color=T.GLASS_BORDER,
            border_width=0,
            command=on_settings,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            right,
            text="✕",
            width=36,
            height=36,
            font=T.FONT_BODY,
            fg_color=T.GLASS_BG,
            hover_color=T.STATUS_ERROR,
            border_width=0,
            command=on_close,
        ).pack(side="right", padx=4)

    def update_status(self, phase: str, model: str) -> None:
        if model:
            self._model_label.configure(text=model)

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
        self._provider_label.configure(text=provider_display_name(provider))

        if phase in {"starting", "busy"}:
            self._pill.set_state("Busy", "busy")
            return
        if phase in {"error", "stopped"}:
            self._pill.set_state("Error", "error")
            return

        if provider == "openai":
            if not openai_configured:
                self._pill.set_state("No API key", "offline")
            elif openai_online:
                self._pill.set_state("Connected", "ready")
            else:
                self._pill.set_state("Offline", "offline")
            return

        if ollama_online:
            self._pill.set_state("Connected", "ready")
        else:
            self._pill.set_state("Offline", "offline")

    def set_ollama_online(self, online: bool) -> None:
        """Backward-compatible hook for legacy Ollama-only updates."""
        if online:
            self._pill.set_state("Connected", "ready")
            self._provider_label.configure(text=provider_display_name("ollama"))
        else:
            self._pill.set_state("Offline", "offline")
            self._provider_label.configure(text="Ollama offline")
