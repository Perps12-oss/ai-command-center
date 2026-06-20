"""Per-zone place() mounting — CTkLabel background stays visible in gaps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.spatial.spec import zone_index


@dataclass
class _ZonePlacement:
    widget: ctk.CTkBaseClass
    zone_id: str
    float_offset: tuple[float, float]
    size_scale: tuple[float, float]


class FrameZoneMount:
    """Attach UI modules at spatial zones via place(); background label stays underneath."""

    def __init__(self, host: ctk.CTkFrame, page_id: str, bg_label: ctk.CTkLabel) -> None:
        self.host = host
        self.page_id = page_id
        self._bg_label = bg_label
        self._placements: list[_ZonePlacement] = []

    def embed_zone_widget(
        self,
        widget: ctk.CTkBaseClass,
        zone_id: str,
        *,
        float_offset: tuple[float, float] = (0.0, 0.0),
        size_scale: tuple[float, float] = (1.0, 1.0),
    ) -> None:
        self._placements.append(
            _ZonePlacement(
                widget=widget,
                zone_id=zone_id,
                float_offset=float_offset,
                size_scale=size_scale,
            )
        )
        self.reposition()

    def _zone_spec(self, zone_id: str) -> dict[str, Any]:
        zones = zone_index(self.page_id)
        if zone_id not in zones:
            raise KeyError(f"unknown zone: {zone_id}")
        return zones[zone_id]

    def reposition(self) -> None:
        for entry in self._placements:
            spec = self._zone_spec(entry.zone_id)
            ax = float(spec["anchor"]["x"]) + entry.float_offset[0]
            ay = float(spec["anchor"]["y"]) + entry.float_offset[1]
            zw = float(spec["size"]["w"]) * entry.size_scale[0]
            zh = float(spec["size"]["h"]) * entry.size_scale[1]
            entry.widget.place(
                in_=self.host,
                relx=ax,
                rely=ay,
                relwidth=zw,
                relheight=zh,
                anchor="center",
            )
            entry.widget.lift(self._bg_label)

        self._bg_label.lower()
