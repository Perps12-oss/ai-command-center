"""Workspace Design System v2 — canonical tokens.

Deep Navy + Soft Purple palette for Modern Chat Workspace v2.
Legacy aliases are mapped to v2 values so existing imports keep working.
"""

from __future__ import annotations

# ── v2 core palette ──────────────────────────────────────────────────────────
APP_BG = "#090B14"
SURFACE_PRIMARY = "#111426"
SURFACE_SECONDARY = "#151933"
SURFACE_ELEVATED = "#1B2040"

ACCENT_PURPLE = "#6C63FF"
ACCENT_PURPLE_HOVER = "#5A52E0"
ACCENT_BLUE = "#4A8CFF"

TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#A5ACD0"
TEXT_MUTED = "#72789C"

SUCCESS_GREEN = "#21C45D"
ERROR_RED = "#FF5A5A"
# Tkinter requires #RRGGBB — pre-composited ~6% white on dark surfaces (design #FFFFFF0F).
BORDER_SUBTLE = "#252A45"

# ── Backgrounds (legacy aliases → v2) ───────────────────────────────────────
BG_DEEP = APP_BG
BG_PANEL = SURFACE_PRIMARY
BG_GLASS = SURFACE_SECONDARY
BG_GLASS_BORDER = "#252A45"
BG_INPUT = "#0D1022"

CANVAS_FALLBACK = BG_DEEP
GLASS_BG = SURFACE_SECONDARY
GLASS_BORDER = BG_GLASS_BORDER
GLASS_BORDER_ALT = BG_GLASS_BORDER
GLASS_BORDER_HOVER = ACCENT_PURPLE
LIGHT_GLASS = SURFACE_ELEVATED

# ── Accent (purple default) ──────────────────────────────────────────────────
ACCENT_DEFAULT = ACCENT_PURPLE
ACCENT_HOVER = ACCENT_PURPLE_HOVER
ACCENT_PRIMARY = ACCENT_DEFAULT

TEXT_HEADING = TEXT_PRIMARY
TEXT_LABEL = TEXT_SECONDARY
TEXT_LOG = TEXT_MUTED
TEXT_SHADOW = "#333333"

# Semantic
STATUS_READY = SUCCESS_GREEN
STATUS_BUSY = "#EAB308"
STATUS_ERROR = ERROR_RED
STATUS_READY_BG = "#1A2E24"
STATUS_BUSY_BG = "#2E2A1A"
STATUS_ERROR_BG = "#2E1A1A"
STATUS_OFFLINE_BG = "#1C1C28"

# Hero / ribbon (purple, no cyan)
HERO_CYAN = ACCENT_PURPLE
HERO_CYAN_DIM = "#2A2559"
HERO_BORDER_IDLE = "#1E1B40"
HERO_BORDER_HOVER = "#3D38AA"
RIBBON_PILL_BG = "#1A1D26"
RIBBON_PILL_BORDER = "#3A3F53"

# Chat message surfaces (doc-style, minimal bubble chrome)
MSG_USER_BG = SURFACE_ELEVATED
MSG_USER_BORDER = BORDER_SUBTLE
MSG_USER_TEXT = TEXT_PRIMARY

MSG_ASSISTANT_BG = "transparent"
MSG_ASSISTANT_BORDER = BORDER_SUBTLE
MSG_ASSISTANT_TEXT = TEXT_PRIMARY

MSG_SYSTEM_BG = BG_INPUT
MSG_SYSTEM_TEXT = TEXT_MUTED

MSG_ERROR_BG = "#2A1010"
MSG_ERROR_BORDER = "#5A2020"
MSG_ERROR_TEXT = ERROR_RED

MSG_TOOL_BG = "#0F1A12"
MSG_TOOL_BORDER = "#1A3A20"
MSG_TOOL_TEXT = "#80C080"

MSG_CANCELLED_TEXT = TEXT_MUTED

# Code blocks inside assistant messages
CODE_BG = "#0D1022"
CODE_BORDER = BORDER_SUBTLE
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
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
SIDEBAR_WIDTH = 240
TOP_BAR_HEIGHT = 64
CHAT_HISTORY_WIDTH = 280
INSPECTOR_WIDTH = 320
COMPOSER_HEIGHT = 76
HEADER_H = TOP_BAR_HEIGHT
CORNER_RADIUS = 10
SMALL_RADIUS = 6
PILL_RADIUS = 12
DIALOG_RADIUS = 12
PROGRESS_RADIUS = 3
BUBBLE_RADIUS = 20
TOAST_RADIUS = 8
PAD = 16
GAP = 16
CARD_RADIUS = 14
BUTTON_RADIUS = 10
INPUT_RADIUS = 20
HERO_RADIUS = 30
CARD_MIN_H = 180
FOOTER_H = 32
SIDEBAR_STRIPE_W = 3

# Animation
FADE_IN_MS = 150
FADE_STEPS = 10
HOVER_MS = 150
BUTTON_HOVER_MS = 100
SELECTION_MS = 200

# Streaming
CHUNK_FLUSH_MS = 50

# Window transparency (< 1.0 lets the desktop wallpaper show through)
WINDOW_ALPHA: float = 0.95

# Theme presets
THEMES: dict[str, dict] = {
    "VS Dark": {
        "accent": ACCENT_PURPLE,
        "bg_deep": APP_BG,
        "bg_panel": SURFACE_PRIMARY,
        "alpha": 0.95,
        "desc": "Deep navy + purple",
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
