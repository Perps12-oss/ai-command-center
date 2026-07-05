"""Settings panel - appearance + connection fields (Phase 4C + Design System v1)."""
from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from ai_command_center.domain.capability_provider_settings import (
    CAPABILITY_KIND_LABELS,
    CAPABILITY_PROVIDER_CHOICES,
    DEFAULT_CAPABILITY_PROVIDER_MAP,
    settings_key_for_kind,
)
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.platform.secret_store import (
    openai_api_key_configured,
    openai_api_key_source,
)
from ai_command_center.providers.defaults import default_model_for_provider
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

        # Custom accent colour
        ctk.CTkLabel(
            appear,
            text="Custom accent colour  (hex, e.g. #FF6B00)",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(anchor="w", padx=T.PAD, pady=(12, 0))
        accent_row = ctk.CTkFrame(appear, fg_color="transparent")
        accent_row.pack(fill="x", padx=T.PAD, pady=(4, 8))
        self._accent_entry = ctk.CTkEntry(
            accent_row,
            placeholder_text="#3B82F6",
            font=T.FONT_BODY,
            height=30,
            width=140,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._accent_entry.pack(side="left")
        self._accent_preview = ctk.CTkFrame(
            accent_row, width=30, height=30,
            fg_color=T.ACCENT_DEFAULT,
            corner_radius=T.SMALL_RADIUS,
        )
        self._accent_preview.pack(side="left", padx=(6, 0))
        self._accent_entry.bind("<KeyRelease>", self._on_accent_key)
        ctk.CTkButton(
            accent_row,
            text="Apply",
            width=60, height=30,
            font=T.FONT_SMALL,
            fg_color=T.ACCENT_DEFAULT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=T.SMALL_RADIUS,
            command=self._apply_custom_accent,
        ).pack(side="left", padx=(6, 0))

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

        ctk.CTkLabel(form, text="LLM provider", text_color=T.TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(8, 0)
        )
        self._provider = ctk.CTkComboBox(
            form,
            values=["ollama", "openai"],
            width=280,
            command=self._on_provider_change,
        )
        self._provider.set("ollama")
        self._provider.pack(anchor="w", padx=16, pady=(4, 8))

        self._default_model = self._field(form, "Default model", "llama3.2:3b")
        self._summarize_model = self._field(form, "Summarize model", "llama3.2:3b")

        self._ollama_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._ollama_frame.pack(fill="x")
        self._ollama_url = self._field(
            self._ollama_frame, "Ollama URL", "http://localhost:11434"
        )

        self._openai_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._openai_base_url = self._field(
            self._openai_frame,
            "OpenAI-compatible base URL",
            "https://api.openai.com/v1",
        )
        self._openai_api_key = self._field(self._openai_frame, "API key", "", show="*")
        self._openai_key_hint = ctk.CTkLabel(
            self._openai_frame,
            text="Leave blank to keep an existing key. OPENAI_API_KEY env var overrides.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self._openai_key_hint.pack(anchor="w", padx=16, pady=(0, 4))

        self._hotkey_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._hotkey_frame.pack(fill="x")
        self._hotkey = self._field(self._hotkey_frame, "Hotkey", "alt+space")
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

        # QwenPaw sidecar section
        qwenpaw = GlassCard(scroll)
        qwenpaw.pack(fill="x", padx=T.PAD, pady=(0, 8))

        ctk.CTkLabel(
            qwenpaw,
            text="QWENPAW SIDECAR",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._qwenpaw_enabled = ctk.CTkCheckBox(qwenpaw, text="Enable QwenPaw sidecar")
        self._qwenpaw_enabled.pack(anchor="w", padx=16, pady=(8, 4))
        self._qwenpaw_url = self._field(qwenpaw, "QwenPaw URL", "http://127.0.0.1:8088")
        self._qwenpaw_agent_id = self._field(qwenpaw, "QwenPaw agent id", "default")
        self._qwenpaw_python = self._field(
            qwenpaw,
            "Python executable (3.13 venv for sidecar)",
            "",
        )
        self._qwenpaw_auto_start = ctk.CTkCheckBox(qwenpaw, text="Auto-start sidecar on launch")
        self._qwenpaw_auto_start.pack(anchor="w", padx=16, pady=(4, 8))

        # Capability providers section
        providers = GlassCard(scroll)
        providers.pack(fill="x", padx=T.PAD, pady=(0, 8))

        ctk.CTkLabel(
            providers,
            text="CAPABILITY PROVIDERS",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        ctk.CTkLabel(
            providers,
            text="Route each capability to Native ACC, QwenPaw, or Auto (default policy).",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            wraplength=640,
            justify="left",
        ).pack(anchor="w", padx=T.PAD, pady=(0, 8))

        self._capability_providers: dict[str, ctk.CTkComboBox] = {}
        provider_labels = {
            "native": "Native",
            "qwenpaw": "QwenPaw",
            "auto": "Auto",
        }
        combo_values = [provider_labels[p] for p in CAPABILITY_PROVIDER_CHOICES]
        for kind in DEFAULT_CAPABILITY_PROVIDER_MAP:
            label = CAPABILITY_KIND_LABELS.get(kind, kind.title())
            ctk.CTkLabel(providers, text=label, text_color=T.TEXT_MUTED).pack(
                anchor="w", padx=16, pady=(8, 0)
            )
            combo = ctk.CTkComboBox(
                providers,
                values=combo_values,
                width=280,
                command=lambda _v, k=kind: self._on_capability_provider_change(k),
            )
            combo.pack(anchor="w", padx=16, pady=(4, 4))
            self._capability_providers[kind] = combo

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
        self._update_provider_fields("ollama")
        self._building = False

    def _field(
        self, parent, label: str, default: str, *, show: str | None = None
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, text_color=T.TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(8, 0)
        )
        entry = ctk.CTkEntry(parent, width=420, show=show or "")
        entry.insert(0, default)
        entry.pack(anchor="w", padx=16, pady=(4, 4))
        return entry

    _PROVIDER_LABEL_TO_VALUE = {
        "Native": "native",
        "QwenPaw": "qwenpaw",
        "Auto": "auto",
    }
    _PROVIDER_VALUE_TO_LABEL = {v: k for k, v in _PROVIDER_LABEL_TO_VALUE.items()}

    def _on_capability_provider_change(self, kind: str) -> None:
        if self._building:
            return
        combo = self._capability_providers.get(kind)
        if combo is None:
            return
        label = combo.get().strip()
        value = self._PROVIDER_LABEL_TO_VALUE.get(label, "auto")
        self._on_save(settings_key_for_kind(kind), value)

    def _set_capability_provider(self, kind: str, value: str) -> None:
        combo = self._capability_providers.get(kind)
        if combo is None:
            return
        normalized = value if value in CAPABILITY_PROVIDER_CHOICES else "auto"
        combo.set(self._PROVIDER_VALUE_TO_LABEL.get(normalized, "Auto"))

    def _on_provider_change(self, value: str) -> None:
        self._update_provider_fields(value)
        model = default_model_for_provider(value.strip())
        self._set_entry(self._default_model, model)
        self._set_entry(self._summarize_model, model)
        if not self._building:
            self._on_save("provider", value.strip())

    def _update_provider_fields(self, provider: str) -> None:
        if provider == "openai":
            self._ollama_frame.pack_forget()
            self._openai_frame.pack(fill="x", before=self._hotkey_frame)
        else:
            self._openai_frame.pack_forget()
            self._ollama_frame.pack(fill="x", before=self._hotkey_frame)

    @staticmethod
    def _valid_hex(color: str) -> bool:
        c = color.strip()
        if not c.startswith("#"):
            return False
        rest = c[1:]
        return len(rest) in (3, 6) and all(ch in "0123456789abcdefABCDEF" for ch in rest)

    def _on_accent_key(self, _event=None) -> None:
        color = self._accent_entry.get().strip()
        if self._valid_hex(color):
            try:
                self._accent_preview.configure(fg_color=color)
            except Exception:
                pass

    def _apply_custom_accent(self) -> None:
        color = self._accent_entry.get().strip()
        if not self._valid_hex(color):
            self._status.configure(
                text="Invalid hex colour. Use format #RRGGBB.", text_color=T.STATUS_ERROR
            )
            return
        theme_manager.set_accent(color)
        self._on_save("accent_color", color)
        self._status.configure(text=f"Accent colour applied: {color}", text_color=T.STATUS_READY)

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
        provider = getattr(settings, "provider", "ollama")
        provider = provider if provider in ("ollama", "openai") else "ollama"
        self._provider.set(provider)
        self._set_entry(self._ollama_url, settings.ollama_url)
        openai_base = getattr(settings, "openai_base_url", "https://api.openai.com/v1")
        self._set_entry(self._openai_base_url, openai_base)
        openai_key = getattr(settings, "openai_api_key", "")
        if openai_api_key_configured(openai_key):
            self._set_entry(self._openai_api_key, "")
            source = openai_api_key_source(openai_key)
            source_labels = {
                "env": "API key active from OPENAI_API_KEY environment variable.",
                "keyring": "API key stored in OS keyring.",
                "settings": "API key stored in local settings.",
            }
            self._openai_key_hint.configure(
                text=source_labels.get(source, "API key configured.")
            )
        else:
            self._set_entry(self._openai_api_key, openai_key)
            self._openai_key_hint.configure(
                text="Leave blank to keep an existing key. OPENAI_API_KEY env var overrides."
            )
        self._update_provider_fields(provider)
        self._set_entry(self._hotkey, settings.hotkey)
        vault = getattr(settings, "obsidian_vault_path", "")
        self._set_entry(self._vault, vault)
        mode = getattr(settings, "overlay_mode", "palette")
        self._overlay_mode.set(mode if mode in ("palette", "compact") else "palette")
        if str(settings.low_memory_mode).lower() in ("true", "1", "yes"):
            self._low_memory.select()
        else:
            self._low_memory.deselect()

        qwenpaw_enabled = getattr(settings, "qwenpaw_enabled", False)
        if str(qwenpaw_enabled).lower() in ("true", "1", "yes"):
            self._qwenpaw_enabled.select()
        else:
            self._qwenpaw_enabled.deselect()
        self._set_entry(self._qwenpaw_url, getattr(settings, "qwenpaw_url", "http://127.0.0.1:8088"))
        self._set_entry(self._qwenpaw_agent_id, getattr(settings, "qwenpaw_agent_id", "default"))
        self._set_entry(self._qwenpaw_python, getattr(settings, "qwenpaw_python", ""))
        if str(getattr(settings, "qwenpaw_auto_start", False)).lower() in ("true", "1", "yes"):
            self._qwenpaw_auto_start.select()
        else:
            self._qwenpaw_auto_start.deselect()

        provider_map = getattr(settings, "capability_provider_map", None) or {}
        for kind in DEFAULT_CAPABILITY_PROVIDER_MAP:
            self._set_capability_provider(kind, str(provider_map.get(kind, "auto")))

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
            "provider": self._provider.get().strip(),
            "default_model": self._default_model.get().strip(),
            "summarize_model": self._summarize_model.get().strip(),
            "ollama_url": self._ollama_url.get().strip(),
            "openai_base_url": self._openai_base_url.get().strip(),
            "openai_api_key": self._openai_api_key.get().strip(),
            "hotkey": self._hotkey.get().strip(),
            "obsidian_vault_path": vault,
            "overlay_mode": self._overlay_mode.get().strip(),
            "low_memory_mode": "true" if self._low_memory.get() else "false",
            "qwenpaw_enabled": "true" if self._qwenpaw_enabled.get() else "false",
            "qwenpaw_url": self._qwenpaw_url.get().strip(),
            "qwenpaw_agent_id": self._qwenpaw_agent_id.get().strip(),
            "qwenpaw_python": self._qwenpaw_python.get().strip(),
            "qwenpaw_auto_start": "true" if self._qwenpaw_auto_start.get() else "false",
        }
        for kind in DEFAULT_CAPABILITY_PROVIDER_MAP:
            combo = self._capability_providers.get(kind)
            if combo is None:
                continue
            label = combo.get().strip()
            pairs[settings_key_for_kind(kind)] = self._PROVIDER_LABEL_TO_VALUE.get(
                label, "auto"
            )
        for key, value in pairs.items():
            if key == "obsidian_vault_path" or value:
                self._on_save(key, value)
        self._update_vault_banner(vault)
        self._status.configure(text="Settings saved.", text_color=T.TEXT_MUTED)
