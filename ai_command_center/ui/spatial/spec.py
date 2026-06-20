"""Spatial map spec loader."""

from __future__ import annotations

from typing import Any

from ai_command_center.repositories.spatial_repository import SpatialRepository


def load_spatial_map(page_id: str | None = None) -> dict[str, Any]:
    data = SpatialRepository().load_spatial_map()
    if page_id is None:
        return data
    maps = data.get("maps", {})
    if page_id not in maps:
        raise KeyError(f"spatial map missing for page: {page_id}")
    return data


def get_page_map(page_id: str) -> dict[str, Any]:
    return dict(load_spatial_map()["maps"][page_id])


def zone_index(page_id: str) -> dict[str, dict[str, Any]]:
    page = get_page_map(page_id)
    return {z["id"]: z for z in page.get("zones", [])}
