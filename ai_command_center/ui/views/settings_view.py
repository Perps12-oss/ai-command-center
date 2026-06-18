"""Settings panel — mutates via settings.set_request only (Phase 4C)."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, *, on_save) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_save = on_save
        self._building = True

        title = ctk.CTkLabel(
            self,
            text="Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        )
        title.pack(anchor="w", padx=T.PAD, pady=(T.PAD, 12))

        form = ctk.CTkFrame(self, fg_color=T.BG_GLASS, corner_radius=T.CORNER_RADIUS)
        form.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

        self._default_model = self._field(form, "Default model", "llama3.2:3b")
        self._summarize_model = self._field(form, "Summarize model", "llama3.2:3b")
        self._ollama_url = self._field(form, "Ollama URL", "http://localhost:11434")
        self._hotkey = self._field(form, "Hotkey", "alt+space")
        self._vault = self._field(form, "Obsidian vault path", "")
        self._overlay_mode = ctk.CTkComboBox(
            form,
            values=["palette", "compact"],
            width=280,
        )
        ctk.CTkLabel(form, text="Overlay mode", text_color=T.TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(8, 0)
        )
        self._overlay_mode.pack(anchor="w", padx=16, pady=(4, 8))

        self._low_memory = ctk.CTkCheckBox(form, text="Low memory mode")
        self._low_memory.pack(anchor="w", padx=16, pady=8)

        save = ctk.CTkButton(form, text="Save settings", command=self._save)
        save.pack(anchor="w", padx=16, pady=(8, 16))

        self._status = ctk.CTkLabel(
            self, text="", text_color=T.TEXT_MUTED, wraplength=600, justify="left"
        )
        self._status.pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))
        self._building = False

    def _field(self, parent, label: str, default: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, text_color=T.TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(8, 0)
        )
        entry = ctk.CTkEntry(parent, width=420)
        entry.insert(0, default)
        entry.pack(anchor="w", padx=16, pady=(4, 4))
        return entry

    def load_from_snapshot(self, settings) -> None:
        self._building = True
        self._set_entry(self._default_model, settings.default_model)
        summarize = getattr(settings, "summarize_model", settings.default_model)
        self._set_entry(self._summarize_model, summarize)
        self._set_entry(self._ollama_url, settings.ollama_url)
        self._set_entry(self._hotkey, settings.hotkey)
        vault = getattr(settings, "obsidian_vault_path", "")
        self._set_entry(self._vault, vault)
        mode = getattr(settings, "overlay_mode", "palette")
        self._overlay_mode.set(mode if mode in ("palette", "compact") else "palette")
        if str(settings.low_memory_mode).lower() in ("true", "1", "yes"):
            self._low_memory.select()
        else:
            self._low_memory.deselect()
        self._building = False

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def _save(self) -> None:
        pairs = {
            "default_model": self._default_model.get().strip(),
            "summarize_model": self._summarize_model.get().strip(),
            "ollama_url": self._ollama_url.get().strip(),
            "hotkey": self._hotkey.get().strip(),
            "obsidian_vault_path": self._vault.get().strip(),
            "overlay_mode": self._overlay_mode.get().strip(),
            "low_memory_mode": "true" if self._low_memory.get() else "false",
        }
        for key, value in pairs.items():
            if value:
                self._on_save(key, value)
        self._status.configure(text="Settings saved.")
