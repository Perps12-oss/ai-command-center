"""Settings panel — appearance section + connection fields (Phase 4C)."""
from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T


class _Swatch(ctk.CTkFrame):
    """Clickable theme colour swatch with label and active ring."""

    def __init__(self, master, name: str, accent: str, desc: str, on_select) -> None:
        super().__init__(master, fg_color="transparent")
        self._name      = name
        self._on_select = on_select
        self._active    = False

        self._ring = ctk.CTkFrame(
            self,
            width=40,
            height=40,
            fg_color=accent,
            corner_radius=20,
            border_color="transparent",
            border_width=2,
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

        # Forward clicks on the label too
        self._lbl.bind("<Button-1>", lambda _: on_select(name))

    def set_active(self, active: bool) -> None:
        self._active = active
        self._ring.configure(
            border_color=T.TEXT_PRIMARY if active else "transparent",
            border_width=3 if active else 2,
        )
        self._lbl.configure(
            text_color=T.TEXT_PRIMARY if active else T.TEXT_MUTED,
            font=(T.FONT_FAMILY, 10, "bold") if active else (T.FONT_FAMILY, 10),
        )


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, *, on_save) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_save    = on_save
        self._building   = True
        self._swatches: dict[str, _Swatch] = {}
        self._active_theme = "VS Dark"

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        title = ctk.CTkLabel(
            scroll,
            text="Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        )
        title.pack(anchor="w", padx=T.PAD, pady=(T.PAD, 12))

        # ── Appearance ─────────────────────────────────────────────────────────
        appear = ctk.CTkFrame(
            scroll, fg_color=T.BG_GLASS, corner_radius=T.CORNER_RADIUS
        )
        appear.pack(fill="x", padx=T.PAD, pady=(0, 12))

        ctk.CTkLabel(
            appear,
            text="APPEARANCE",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        # Theme swatches row
        ctk.CTkLabel(
            appear,
            text="Theme",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(anchor="w", padx=T.PAD, pady=(4, 0))

        swatches_row = ctk.CTkFrame(appear, fg_color="transparent")
        swatches_row.pack(fill="x", padx=T.PAD, pady=(6, 8))

        for name, cfg in T.THEMES.items():
            sw = _Swatch(
                swatches_row,
                name,
                cfg["accent"],
                cfg.get("desc", ""),
                self._on_theme_select,
            )
            sw.pack(side="left", padx=(0, 16))
            self._swatches[name] = sw

        self._swatches.get("VS Dark", None) and self._swatches["VS Dark"].set_active(True)

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

        # ── Connection settings ─────────────────────────────────────────────────
        form = ctk.CTkFrame(
            scroll, fg_color=T.BG_GLASS, corner_radius=T.CORNER_RADIUS
        )
        form.pack(fill="x", padx=T.PAD, pady=(0, 12))

        ctk.CTkLabel(
            form,
            text="CONNECTION",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._default_model   = self._field(form, "Default model",    "llama3.2:3b")
        self._summarize_model = self._field(form, "Summarize model",  "llama3.2:3b")
        self._ollama_url      = self._field(form, "Ollama URL",       "http://localhost:11434")
        self._hotkey          = self._field(form, "Hotkey",           "alt+space")
        self._vault           = self._field(form, "Obsidian vault path", "")

        ctk.CTkLabel(
            form, text="Overlay mode", text_color=T.TEXT_MUTED
        ).pack(anchor="w", padx=T.PAD, pady=(8, 0))

        self._overlay_mode = ctk.CTkComboBox(
            form, values=["palette", "compact"], width=280
        )
        self._overlay_mode.pack(anchor="w", padx=T.PAD, pady=(4, 8))

        self._low_memory = ctk.CTkCheckBox(form, text="Low memory mode")
        self._low_memory.pack(anchor="w", padx=T.PAD, pady=8)

        # ── Save button ────────────────────────────────────────────────────────
        save = ctk.CTkButton(
            scroll,
            text="Save settings",
            command=self._save,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
        )
        save.pack(anchor="w", padx=T.PAD, pady=(4, 4))

        self._status = ctk.CTkLabel(
            scroll,
            text="",
            text_color=T.TEXT_MUTED,
            wraplength=600,
            justify="left",
        )
        self._status.pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))

        self._building = False

    # ── theme / opacity callbacks ───────────────────────────────────────────────

    def _on_theme_select(self, name: str) -> None:
        self._active_theme = name
        for n, sw in self._swatches.items():
            sw.set_active(n == name)
        if not self._building:
            self._on_save("theme", name)
            alpha = T.THEMES.get(name, {}).get("alpha", T.WINDOW_ALPHA)
            self._opacity_slider.set(alpha)
            self._opacity_lbl.configure(text=f"{int(alpha * 100)}%")
            self._on_save("window_alpha", str(alpha))
            self._status.configure(text=f'Theme "{name}" applied.')

    def _on_opacity_change(self, value: float) -> None:
        self._opacity_lbl.configure(text=f"{int(value * 100)}%")
        if not self._building:
            self._on_save("window_alpha", str(round(value, 2)))

    # ── helpers ────────────────────────────────────────────────────────────────

    def _field(self, parent, label: str, default: str) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent, text=label, text_color=T.TEXT_MUTED
        ).pack(anchor="w", padx=T.PAD, pady=(8, 0))
        entry = ctk.CTkEntry(parent, width=420)
        entry.insert(0, default)
        entry.pack(anchor="w", padx=T.PAD, pady=(4, 4))
        return entry

    def load_from_snapshot(self, settings) -> None:
        self._building = True
        self._set_entry(self._default_model,   settings.default_model)
        summarize = getattr(settings, "summarize_model", settings.default_model)
        self._set_entry(self._summarize_model, summarize)
        self._set_entry(self._ollama_url,      settings.ollama_url)
        self._set_entry(self._hotkey,          settings.hotkey)
        vault = getattr(settings, "obsidian_vault_path", "")
        self._set_entry(self._vault, vault)
        mode = getattr(settings, "overlay_mode", "palette")
        self._overlay_mode.set(mode if mode in ("palette", "compact") else "palette")
        if str(settings.low_memory_mode).lower() in ("true", "1", "yes"):
            self._low_memory.select()
        else:
            self._low_memory.deselect()
        theme = getattr(settings, "theme", "VS Dark")
        if theme in self._swatches:
            self._active_theme = theme
            for n, sw in self._swatches.items():
                sw.set_active(n == theme)
        alpha_raw = getattr(settings, "window_alpha", str(T.WINDOW_ALPHA))
        try:
            alpha = float(alpha_raw)
            self._opacity_slider.set(alpha)
            self._opacity_lbl.configure(text=f"{int(alpha * 100)}%")
        except (ValueError, TypeError):
            pass
        self._building = False

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def _save(self) -> None:
        pairs = {
            "default_model":       self._default_model.get().strip(),
            "summarize_model":     self._summarize_model.get().strip(),
            "ollama_url":          self._ollama_url.get().strip(),
            "hotkey":              self._hotkey.get().strip(),
            "obsidian_vault_path": self._vault.get().strip(),
            "overlay_mode":        self._overlay_mode.get().strip(),
            "low_memory_mode":     "true" if self._low_memory.get() else "false",
            "theme":               self._active_theme,
            "window_alpha":        str(round(self._opacity_slider.get(), 2)),
        }
        for key, value in pairs.items():
            if value:
                self._on_save(key, value)
        self._status.configure(text="Settings saved.")
