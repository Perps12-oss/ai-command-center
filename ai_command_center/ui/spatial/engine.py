"""Zone-anchored layout — UI modules attach to spatial map coordinates."""

from __future__ import annotations

from typing import Any, Protocol

import customtkinter as ctk

from ai_command_center.ui.spatial.spec import get_page_map, zone_index


class _ZoneMount(Protocol):
    def embed_zone_widget(
        self,
        widget: ctk.CTkBaseClass,
        zone_id: str,
        *,
        float_offset: tuple[float, float] = (0.0, 0.0),
        size_scale: tuple[float, float] = (1.0, 1.0),
    ) -> None: ...


class SpatialLayoutEngine:
    """Places widgets at normalized UV anchors — each is a separate canvas window."""

    def __init__(self, mount: _ZoneMount, page_id: str) -> None:
        self.page_id = page_id
        self._mount = mount
        self._zones = zone_index(page_id)
        self._map = get_page_map(page_id)

    def zone(self, zone_id: str) -> dict[str, Any]:
        if zone_id not in self._zones:
            raise KeyError(f"unknown zone: {zone_id}")
        return self._zones[zone_id]

    def attach(
        self,
        widget: ctk.CTkBaseClass,
        zone_id: str,
        *,
        float_offset: tuple[float, float] = (0.0, 0.0),
        size_scale: tuple[float, float] = (1.0, 1.0),
    ) -> None:
        self._mount.embed_zone_widget(
            widget,
            zone_id,
            float_offset=float_offset,
            size_scale=size_scale,
        )
