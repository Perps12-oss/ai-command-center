"""Runtime theme application.

Applies window-level alpha and mutates design-system tokens so panels
pick up Light / High Contrast / accent changes without restart.
"""

from __future__ import annotations

from ai_command_center.ui.design_system import theme_v2 as T

_active_name: str = "VS Dark"
_active_alpha: float = T.WINDOW_ALPHA
_custom_accent: str | None = None

# Defaults captured once so we can restore when switching presets.
_DEFAULT_TOKENS: dict[str, str] = {
    "BG_DEEP": T.BG_DEEP,
    "BG_PANEL": T.BG_PANEL,
    "BG_GLASS": T.BG_GLASS,
    "BG_GLASS_BORDER": T.BG_GLASS_BORDER,
    "BG_INPUT": T.BG_INPUT,
    "GLASS_BG": T.GLASS_BG,
    "GLASS_BORDER": T.GLASS_BORDER,
    "TEXT_PRIMARY": T.TEXT_PRIMARY,
    "TEXT_SECONDARY": T.TEXT_SECONDARY,
    "TEXT_MUTED": T.TEXT_MUTED,
    "ACCENT_DEFAULT": T.ACCENT_DEFAULT,
    "MSG_USER_BG": T.MSG_USER_BG,
    "MSG_USER_BORDER": T.MSG_USER_BORDER,
    "MSG_USER_TEXT": T.MSG_USER_TEXT,
    "MSG_ASSISTANT_BG": T.MSG_ASSISTANT_BG,
    "MSG_ASSISTANT_BORDER": T.MSG_ASSISTANT_BORDER,
    "MSG_ASSISTANT_TEXT": T.MSG_ASSISTANT_TEXT,
}


def theme_names() -> list[str]:
    return list(T.THEMES.keys())


def active_name() -> str:
    return _active_name


def active_alpha() -> float:
    return _active_alpha


def active_accent() -> str:
    if _custom_accent:
        return _custom_accent
    return T.THEMES.get(_active_name, {}).get("accent", T.ACCENT_DEFAULT)


def set_accent(color: str) -> None:
    """Override the runtime accent colour. Mutates the theme token in-process."""
    global _custom_accent
    _custom_accent = color
    T.ACCENT_DEFAULT = color  # type: ignore[assignment]
    T.ACCENT_HOVER = color  # type: ignore[assignment]
    T.ACCENT_PRIMARY = color  # type: ignore[assignment]


def _normalize_theme(name: str) -> str:
    """Map legacy theme names to the design system presets."""
    if name in T.THEMES:
        return name
    key = str(name or "").strip().lower()
    if key in {"dark", "vs dark", "vsdark"}:
        return "VS Dark"
    if key in {"light"}:
        return "Light"
    if key in {"high contrast", "highcontrast", "hc", "contrast"}:
        return "High Contrast"
    if key in {"golden hour", "golden_hour", "goldenhour"}:
        return "Golden Hour"
    return "VS Dark"


def _apply_palette(preset: dict) -> None:
    """Mutate module-level theme tokens from a THEMES preset."""
    T.BG_DEEP = str(preset.get("bg_deep", _DEFAULT_TOKENS["BG_DEEP"]))  # type: ignore[assignment]
    T.BG_PANEL = str(preset.get("bg_panel", _DEFAULT_TOKENS["BG_PANEL"]))  # type: ignore[assignment]
    T.BG_GLASS = str(preset.get("bg_glass", preset.get("bg_panel", _DEFAULT_TOKENS["BG_GLASS"])))  # type: ignore[assignment]
    T.BG_INPUT = str(preset.get("bg_input", _DEFAULT_TOKENS["BG_INPUT"]))  # type: ignore[assignment]
    border = str(preset.get("glass_border", _DEFAULT_TOKENS["BG_GLASS_BORDER"]))
    T.BG_GLASS_BORDER = border  # type: ignore[assignment]
    T.GLASS_BG = T.BG_GLASS  # type: ignore[assignment]
    T.GLASS_BORDER = border  # type: ignore[assignment]
    T.CONTEXT_BAR_BG = T.BG_GLASS  # type: ignore[assignment]
    T.TEXT_PRIMARY = str(preset.get("text_primary", _DEFAULT_TOKENS["TEXT_PRIMARY"]))  # type: ignore[assignment]
    T.TEXT_SECONDARY = str(preset.get("text_secondary", _DEFAULT_TOKENS["TEXT_SECONDARY"]))  # type: ignore[assignment]
    T.TEXT_MUTED = str(preset.get("text_muted", _DEFAULT_TOKENS["TEXT_MUTED"]))  # type: ignore[assignment]
    T.TEXT_HEADING = T.TEXT_PRIMARY  # type: ignore[assignment]
    T.TEXT_LABEL = T.TEXT_SECONDARY  # type: ignore[assignment]
    accent = str(preset.get("accent", _DEFAULT_TOKENS["ACCENT_DEFAULT"]))
    if _custom_accent is None:
        T.ACCENT_DEFAULT = accent  # type: ignore[assignment]
        T.ACCENT_HOVER = accent  # type: ignore[assignment]
        T.ACCENT_PRIMARY = accent  # type: ignore[assignment]
    T.MSG_USER_BG = str(preset.get("msg_user_bg", _DEFAULT_TOKENS["MSG_USER_BG"]))  # type: ignore[assignment]
    T.MSG_USER_BORDER = str(preset.get("msg_user_border", _DEFAULT_TOKENS["MSG_USER_BORDER"]))  # type: ignore[assignment]
    T.MSG_USER_TEXT = str(preset.get("msg_user_text", _DEFAULT_TOKENS["MSG_USER_TEXT"]))  # type: ignore[assignment]
    T.MSG_ASSISTANT_BG = str(preset.get("msg_assistant_bg", _DEFAULT_TOKENS["MSG_ASSISTANT_BG"]))  # type: ignore[assignment]
    T.MSG_ASSISTANT_BORDER = str(preset.get("msg_assistant_border", _DEFAULT_TOKENS["MSG_ASSISTANT_BORDER"]))  # type: ignore[assignment]
    T.MSG_ASSISTANT_TEXT = str(preset.get("msg_assistant_text", _DEFAULT_TOKENS["MSG_ASSISTANT_TEXT"]))  # type: ignore[assignment]
    appearance = str(preset.get("appearance", "dark"))
    try:
        import customtkinter as ctk

        ctk.set_appearance_mode("light" if appearance == "light" else "dark")
    except Exception:
        pass


def apply(window, *, theme_name: str | None = None, alpha: float | None = None) -> None:
    """Apply theme preset and/or opacity to *window*.

    Safe to call from the main thread at any time.
    Mutates theme_v2 tokens so existing widgets that read T.* on configure
    pick up Light / High Contrast palettes.
    """
    global _active_name, _active_alpha

    if theme_name is not None:
        _active_name = _normalize_theme(theme_name)
        preset = T.THEMES.get(_active_name, {})
        if preset:
            _apply_palette(preset)
            if alpha is None and "alpha" in preset:
                _active_alpha = max(0.5, min(1.0, float(preset["alpha"])))

    if alpha is not None:
        _active_alpha = max(0.5, min(1.0, float(alpha)))

    try:
        window.attributes("-alpha", _active_alpha)
    except Exception:
        pass

    # Best-effort root recolor for immediate feedback
    try:
        window.configure(fg_color=T.BG_DEEP)
    except Exception:
        pass
