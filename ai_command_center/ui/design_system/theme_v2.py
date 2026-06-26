"""Workspace Design System v1 — canonical tokens.

Merges the Replit dark dashboard palette with the OneDrive token surface
so existing components can import `tokens as T` without breaking.
"""

from __future__ import annotations

# Backgrounds — Replit dark dashboard palette
BG_DEEP = "#0D0D1A"
BG_PANEL = "#16162A"
BG_GLASS = "#1A1A2E"
BG_GLASS_BORDER = "#2A2A4A"
BG_INPUT = "#12121F"

# Legacy OneDrive aliases (kept for compatibility)
CANVAS_FALLBACK = BG_DEEP
GLASS_BG = BG_GLASS
GLASS_BORDER = BG_GLASS_BORDER
GLASS_BORDER_ALT = BG_GLASS_BORDER
GLASS_BORDER_HOVER = "#00FFFF"
LIGHT_GLASS = "#24243A"

# Accent
ACCENT_DEFAULT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
ACCENT_PRIMARY = ACCENT_DEFAULT

# Text
TEXT_PRIMARY = "#F0F0F5"
TEXT_SECONDARY = "#A0A0B8"
TEXT_MUTED = "#6B6B80"
TEXT_HEADING = TEXT_PRIMARY
TEXT_LABEL = TEXT_SECONDARY
TEXT_LOG = TEXT_MUTED
TEXT_SHADOW = "#333333"

# Semantic
STATUS_READY = "#22C55E"
STATUS_BUSY = "#EAB308"
STATUS_ERROR = "#EF4444"
STATUS_READY_BG = "#1A2E24"
STATUS_BUSY_BG = "#2E2A1A"
STATUS_ERROR_BG = "#2E1A1A"
STATUS_OFFLINE_BG = "#1C1C28"

# Hero / ribbon (ActionRibbon pills + HeroPanel)
HERO_CYAN = "#00FFFF"
HERO_CYAN_DIM = "#1A4A52"
HERO_BORDER_IDLE = "#124853"
HERO_BORDER_HOVER = "#1A6B75"
RIBBON_PILL_BG = "#1A1D26"
RIBBON_PILL_BORDER = "#3A3F53"

# Chat message bubbles
MSG_USER_BG = "#1E2D4A"
MSG_USER_BORDER = "#2D4A7A"
MSG_USER_TEXT = "#C8DEFF"

MSG_ASSISTANT_BG = "#1A1A2E"
MSG_ASSISTANT_BORDER = "#2A2A4A"
MSG_ASSISTANT_TEXT = "#E8E8F0"

MSG_SYSTEM_BG = "#12121F"
MSG_SYSTEM_TEXT = "#6B6B80"

MSG_ERROR_BG = "#2A1010"
MSG_ERROR_BORDER = "#5A2020"
MSG_ERROR_TEXT = "#FF8080"

MSG_TOOL_BG = "#0F1A12"
MSG_TOOL_BORDER = "#1A3A20"
MSG_TOOL_TEXT = "#80C080"

MSG_CANCELLED_TEXT = "#6B6B80"

# Code blocks inside assistant messages
CODE_BG = "#0A0A14"
CODE_BORDER = "#222240"
CODE_TEXT = "#A0C8FF"

# Typography
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_HEADER = (FONT_FAMILY, 13, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_SMALL = (FONT_FAMILY, 11)
FONT_MONO = ("Consolas", 11)
FONT_ROLE = (FONT_FAMILY, 10, "bold")

# Layout
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 700
SIDEBAR_WIDTH = 200
TOP_BAR_HEIGHT = 52
HEADER_H = TOP_BAR_HEIGHT
CORNER_RADIUS = 10
PAD = 16
GAP = 16
CARD_RADIUS = CORNER_RADIUS
HERO_RADIUS = 30
CARD_MIN_H = 180
FOOTER_H = 32
SIDEBAR_STRIPE_W = 3

# Animation
FADE_IN_MS = 150
FADE_STEPS = 10

# Streaming
CHUNK_FLUSH_MS = 50

# Window transparency (< 1.0 lets the desktop wallpaper show through)
WINDOW_ALPHA: float = 0.95

# Theme presets
THEMES: dict[str, dict] = {
    "VS Dark": {
        "accent": "#0078D4",
        "bg_deep": "#0D0D1A",
        "bg_panel": "#16162A",
        "alpha": 0.95,
        "desc": "Classic VS Code blue",
    },
    "Midnight": {
        "accent": "#9B59B6",
        "bg_deep": "#0A0A14",
        "bg_panel": "#12121E",
        "alpha": 0.92,
        "desc": "Purple dusk",
    },
    "Crimson": {
        "accent": "#E74C3C",
        "bg_deep": "#0D0808",
        "bg_panel": "#1A1010",
        "alpha": 0.91,
        "desc": "Bold red",
    },
    "Forest": {
        "accent": "#27AE60",
        "bg_deep": "#080D08",
        "bg_panel": "#101A10",
        "alpha": 0.91,
        "desc": "Deep green",
    },
    "Ocean": {
        "accent": "#2980B9",
        "bg_deep": "#050D14",
        "bg_panel": "#0A1420",
        "alpha": 0.93,
        "desc": "Deep sea",
    },
}
