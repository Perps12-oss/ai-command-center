"""Background layer spec loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_command_center.repositories.spatial_repository import SpatialRepository

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "backgrounds"



Z_INDEX = {

    "background": 0,

    "depth": 10,

    "motion": 20,

    "ui": 30,

    "modal": 40,

}





def load_background_layer() -> dict[str, Any]:
    return SpatialRepository().load_background_layer()





def _merge_global(page: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:

    global_wp = spec.get("global_wallpaper", {})

    if page.get("inherit") == "global_wallpaper":

        merged = dict(global_wp)

        for key, value in page.items():

            if key != "inherit":

                merged[key] = value

        return merged

    if global_wp and not page.get("image"):

        merged = dict(global_wp)

        merged.update(page)

        return merged

    return dict(page)





def get_page_background(page_id: str) -> dict[str, Any]:

    spec = load_background_layer()

    pages = spec.get("pages", {})

    if page_id in pages:

        return _merge_global(pages[page_id], spec)

    default = spec.get("default_background", {})

    if default.get("inherit") == "global_wallpaper":

        return _merge_global(default, spec)

    return dict(default)





_DESKTOP_FALLBACK = Path(r"C:\Users\S8633\OneDrive\Desktop\sound-waves-abstract-art-4k-yu-1366x768.jpg")





def resolve_image_path(relative: str) -> Path | None:

    rel = relative.replace("backgrounds/", "")

    direct = _ASSETS / rel

    if direct.is_file():

        return direct

    stem = Path(rel).stem

    for ext in (".jpg", ".jpeg", ".png", ".webp"):

        candidate = _ASSETS / f"{stem}{ext}"

        if candidate.is_file():

            return candidate

    if _DESKTOP_FALLBACK.is_file():

        return _DESKTOP_FALLBACK

    return None





def tint_palette() -> list[str]:

    return list(load_background_layer().get("tint_palette", ["#0B0C15"]))





def global_wallpaper_image() -> str:

    spec = load_background_layer()

    return str(spec.get("global_wallpaper", {}).get("image", "backgrounds/command_center_bg.jpg"))


