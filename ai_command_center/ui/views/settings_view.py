"""Settings panel — mutates via settings.set_request only (Phase 4C)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from ai_command_center.ui.components.floating_ui import FLOAT_GAP, FLOAT_PAD, pack_floating
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.layer.layer_stack import PageLayerStack
from ai_command_center.ui.theme import tokens as T


class SettingsView(PageLayerStack):
    def __init__(self, master, *, on_save) -> None:
        super().__init__(master, "settings")
        self._on_save = on_save
        self._building = True

        title_card = GlassCard(self.ui_layer)
        pack_floating(title_card, first=True)
        ctk.CTkLabel(
            title_card,
            text="Settings",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        ).pack(anchor="w", padx=T.PAD, pady=T.PAD)

        self._vault_banner = ctk.CTkLabel(
            self.ui_layer,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            wraplength=640,
            justify="left",
        )
        self._vault_banner.pack(anchor="w", padx=FLOAT_PAD, pady=(0, 8))

        form = GlassCard(self.ui_layer)
        pack_floating(form, fill="x")

        self._default_model = self._field(form, "Default model", "llama3.2:3b")
        self._summarize_model = self._field(form, "Summarize model", "llama3.2:3b")
        self._ollama_url = self._field(form, "Ollama URL", "http://localhost:11434")
        self._hotkey = self._field(form, "Hotkey", "alt+space")
        self._vault = self._field(
            form,
            "Obsidian vault path (folder containing your .md notes)",
            "",
        )
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
            self.ui_layer, text="", text_color=T.TEXT_MUTED, wraplength=600, justify="left"
        )
        self._status.pack(anchor="w", padx=FLOAT_PAD, pady=(0, FLOAT_PAD))
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
        self._update_vault_banner(vault)
        self._building = False

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def _update_vault_banner(self, vault_path: str) -> None:
        path = str(vault_path or "").strip()
        if not path:
            self._vault_banner.configure(
                text="Notes: vault not configured — set folder path below, then Save.",
                text_color=T.STATUS_ERROR,
            )
            return
        resolved = Path(path)
        if resolved.is_dir():
            self._vault_banner.configure(
                text=f"Notes: vault OK — {resolved}",
                text_color=T.STATUS_READY,
            )
        else:
            self._vault_banner.configure(
                text=f"Notes: path not found — {resolved}",
                text_color=T.STATUS_ERROR,
            )

    def _save(self) -> None:
        vault = self._vault.get().strip()
        if vault and not Path(vault).is_dir():
            self._status.configure(
                text=f"Vault path does not exist or is not a folder: {vault}",
                text_color=T.STATUS_ERROR,
            )
            self._update_vault_banner(vault)
            return

        pairs = {
            "default_model": self._default_model.get().strip(),
            "summarize_model": self._summarize_model.get().strip(),
            "ollama_url": self._ollama_url.get().strip(),
            "hotkey": self._hotkey.get().strip(),
            "obsidian_vault_path": vault,
            "overlay_mode": self._overlay_mode.get().strip(),
            "low_memory_mode": "true" if self._low_memory.get() else "false",
        }
        for key, value in pairs.items():
            if key == "obsidian_vault_path" or value:
                self._on_save(key, value)
        self._update_vault_banner(vault)
        self._status.configure(text="Settings saved.", text_color=T.TEXT_MUTED)
