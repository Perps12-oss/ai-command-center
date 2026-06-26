"""Runtime theme application.

Applies window-level alpha and exposes the active accent colour.
No EventBus interaction; app.py calls apply() after receiving a
settings change and forwards the new values to widgets that care.
"""

from __future__ import annotations

from ai_command_center.ui.design_system import theme_v2 as T

_active_name: str = "VS Dark"
_active_alpha: float = T.WINDOW_ALPHA


def theme_names() -> list[str]:
    return list(T.THEMES.keys())


def active_name() -> str:
    return _active_name


def active_alpha() -> float:
    return _active_alpha


def active_accent() -> str:
    return T.THEMES.get(_active_name, {}).get("accent", T.ACCENT_DEFAULT)


def _normalize_theme(name: str) -> str:
    """Map legacy theme names to the design system presets."""
    if name in T.THEMES:
        return name
    if name in {"dark", "light"}:
        return "VS Dark"
    return "VS Dark"


def apply(window, *, theme_name: str | None = None, alpha: float | None = None) -> None:
    """Apply theme preset and/or opacity to *window*.

    Safe to call from the main thread at any time.
    The sidebar and all panels are part of the same window, so the
    window-level alpha change makes the wallpaper visible through every
    panel simultaneously.
    """
    global _active_name, _active_alpha

    if theme_name is not None:
        _active_name = _normalize_theme(theme_name)

    if alpha is not None:
        _active_alpha = max(0.5, min(1.0, float(alpha)))

    try:
        window.attributes("-alpha", _active_alpha)
    except Exception:
        pass
