"""Load hero asset at composition root (not in UI widgets)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image

from ai_command_center.repositories.asset_repository import AssetRepository

_HERO_PATH = (
    Path(__file__).resolve().parent.parent / "ui" / "assets" / "hero_core.png"
)


def load_hero_ctk_image() -> ctk.CTkImage | None:
    """Return resized hero CTkImage or None if asset missing/unreadable."""
    if not _HERO_PATH.is_file():
        return None
    try:
        pil = AssetRepository().load_image(_HERO_PATH)
        pil = pil.resize((320, 80), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=pil, dark_image=pil, size=(320, 80))
    except Exception:
        return None
