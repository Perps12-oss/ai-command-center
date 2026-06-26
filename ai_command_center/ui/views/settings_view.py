"""Settings panel - appearance + connection fields (Phase 4C + Design System v1)."""
from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_manager
from ai_command_center.ui.design_system import theme_v2 as T


class _Swatch(ctk.CTkFrame):
    """Clickable theme colour swatch with label and active ring."""

    def __init__(self, master, name: str, accent: str, on_select) -> None:
        super().__init__(master, fg_color="transparent")
        self._name = name
        self._on_select = on_select

        self._ring = ctk.CTkFrame(
            self,
            width=40,
            height=40,
            fg_color=accent,
            corner_radius=T.BUBBLE_RADIUS,
            border_width=0,
        )
        self._ring.pack()
        self._ring.bind("<Button-1>", lambda _: on_select(name))

        self._lbl = ctk.CTkLabel(
            self,
            text=name,
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
        )
        self._lbl.pack(pady=(3, 0))
        self._lbl.bind("<Button-1>", lambda _: on_select(name))

    def set_active(self, active: bool) -> None:
        if active:
            self._ring.configure(
                border_color=T.TEXT_PRIMARY,
                border_width=3,
            )
        else:
            self._ring.configure(border_width=0)
        self._lbl.configure(
            text_color=T.TEXT_PRIMARY if active else T.TEXT_MUTED,
            font=(T.FONT_FAMILY, 10, "bold") if active else (T.FONT_FAMILY, 10),
        )


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, *, on_save) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_save = on_save
        self._building = True

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        title_card = GlassCard(scroll)
        title_card.pack(fill="x", padx=T.PAD, pady=(T.PAD, 8))
        ctk.CTkLabel(
            title_card,
            text="Settings",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        ).pack(anchor="w", padx=T.PAD, pady=T.PAD)

        self._vault_banner = ctk.CTkLabel(
            scroll,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            wraplength=640,
            justify="left",
        )
        self._vault_banner.pack(anchor="w", padx=T.PAD, pady=(0, 8))

        # Appearance section
        appear = GlassCard(scroll)
        appear.pack(fill="x", padx=T.PAD, pady=(0, 8))

        ctk.CTkLabel(
            appear,
            text="APPEARANCE",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        ctk.CTkLabel(
            appear,
            text="Theme",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(anchor="w", padx=T.PAD, pady=(4, 0))

        swatches_row = ctk.CTkFrame(appear, fg_color="transparent")
        swatches_row.pack(fill="x", padx=T.PAD, pady=(6, 8))

        self._swatches: dict[str, _Swatch] = {}
        for name, cfg in T.THEMES.items():
            sw = _Swatch(
                swatches_row,
                name,
                cfg["accent"],
                self._on_theme_select,
            )
            sw.pack(side="left", padx=(0, 16))
            self._swatches[name] = sw

        # Opacity slider
        ctk.CTkLabel(
            appear,
            text="Window opacity  (lower = more wallpaper visible)",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(anchor="w", padx=T.PAD, pady=(4, 0))

        slider_row = ctk.CTkFrame(appear, fg_color="transparent")
        slider_row.pack(fill="x", padx=T.PAD, pady=(4, T.PAD))

        self._opacity_slider = ctk.CTkSlider(
            slider_row,
            from_=0.5,
            to=1.0,
            number_of_steps=20,
            command=self._on_opacity_change,
        )
        self._opacity_slider.set(T.WINDOW_ALPHA)
        self._opacity_slider.pack(side="left", fill="x", expand=True)

        self._opacity_lbl = ctk.CTkLabel(
            slider_row,
            text=f"{int(T.WINDOW_ALPHA * 100)}%",
            font=T.FONT_SMALL,
            text_color=T.TEXT_SECONDARY,
            width=40,
            anchor="e",
        )
        self._opacity_lbl.pack(side="right", padx=(8, 0))

        # Connection section
        form = GlassCard(scroll)
        form.pack(fill="x", padx=T.PAD, pady=(0, 8))

        ctk.CTkLabel(
            form,
            text="CONNECTION",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._default_model = self._field(form, "Default model", "llama3.2:3b")
        self._summarize_model = self._field(form, "Summarize model", "llama3.2:3b")
        self._ollama_url = self._field(form, "Ollama URL", "http://localhost:11434")
        self._hotkey = self._field(form, "Hotkey", "alt+space")
        self._vault = self._field(
            form,
            "Obsidian vault path (folder containing your .md notes)",
            "",
        )

        ctk.CTkLabel(form, text="Overlay mode", text_color=T.TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(8, 0)
        )
        self._overlay_mode = ctk.CTkComboBox(
            form,
            values=["palette", "compact"],
            width=280,
        )
        self._overlay_mode.pack(anchor="w", padx=16, pady=(4, 8))

        self._low_memory = ctk.CTkCheckBox(form, text="Low memory mode")
        self._low_memory.pack(anchor="w", padx=16, pady=8)

        save = ctk.CTkButton(form, text="Save settings", command=self._save)
        save.pack(anchor="w", padx=16, pady=(8, 16))

        self._status = ctk.CTkLabel(
            scroll,
            text="",
            text_color=T.TEXT_MUTED,
            wraplength=600,
            justify="left",
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

    def _on_theme_select(self, name: str) -> None:
        for n, sw in self._swatches.items():
            sw.set_active(n == name)
        if not self._building:
            self._on_save("theme", name)
            alpha = T.THEMES.get(name, {}).get("alpha", T.WINDOW_ALPHA)
            self._opacity_slider.set(alpha)
            self._opacity_lbl.configure(text=f"{int(alpha * 100)}%")
            self._on_save("window_alpha", str(round(alpha, 2)))
            self._status.configure(text=f'Theme "{name}" applied.')

    def _on_opacity_change(self, value: float) -> None:
        self._opacity_lbl.configure(text=f"{int(value * 100)}%")
        if not self._building:
            self._on_save("window_alpha", str(round(value, 2)))

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

        theme = getattr(settings, "theme", "dark")
        theme_name = theme if theme in T.THEMES else "VS Dark"
        for n, sw in self._swatches.items():
            sw.set_active(n == theme_name)

        alpha = getattr(settings, "window_alpha", T.WINDOW_ALPHA)
        try:
            alpha = float(alpha)
        except (TypeError, ValueError):
            alpha = T.WINDOW_ALPHA
        self._opacity_slider.set(alpha)
        self._opacity_lbl.configure(text=f"{int(alpha * 100)}%")

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
                text="Notes: vault not configured - set folder path below, then Save.",
                text_color=T.STATUS_ERROR,
            )
            return
        resolved = Path(path)
        if resolved.is_dir():
            self._vault_banner.configure(
                text=f"Notes: vault OK - {resolved}",
                text_color=T.STATUS_READY,
            )
        else:
            self._vault_banner.configure(
                text=f"Notes: path not found - {resolved}",
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
