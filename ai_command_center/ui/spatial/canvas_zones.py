"""Zone mounting — canvas create_window (legacy) and overlay place() (preferred)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.spatial.spec import zone_index


@dataclass
class _ZoneWindow:
    widget: Any
    zone_id: str
    float_offset: tuple[float, float]
    size_scale: tuple[float, float]
    win_id: int | None = None


class CanvasZoneMount:
    """Attach UI modules at spatial zones — canvas image stays visible in gaps."""

    def __init__(self, canvas: Any, page_id: str) -> None:
        self.canvas = canvas
        self.page_id = page_id
        self._zone_windows: list[_ZoneWindow] = []
        self._zones_visible = True

    def embed_zone_widget(
        self,
        widget: Any,
        zone_id: str,
        *,
        float_offset: tuple[float, float] = (0.0, 0.0),
        size_scale: tuple[float, float] = (1.0, 1.0),
    ) -> None:
        self._zone_windows.append(
            _ZoneWindow(
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
        if not self._zones_visible:
            return
        canvas = self.canvas
        w = max(canvas.winfo_width(), 1)
        h = max(canvas.winfo_height(), 1)
        if w <= 1 or h <= 1:
            return

        for entry in self._zone_windows:
            spec = self._zone_spec(entry.zone_id)
            ax = float(spec["anchor"]["x"]) + entry.float_offset[0]
            ay = float(spec["anchor"]["y"]) + entry.float_offset[1]
            zw = float(spec["size"]["w"]) * entry.size_scale[0]
            zh = float(spec["size"]["h"]) * entry.size_scale[1]
            px = int(ax * w)
            py = int(ay * h)
            ww = max(int(zw * w), 40)
            wh = max(int(zh * h), 24)

            if entry.win_id is not None:
                canvas.delete(entry.win_id)

            entry.win_id = canvas.create_window(
                px,
                py,
                window=entry.widget,
                anchor="center",
                width=ww,
                height=wh,
                tags=("zone_ui", entry.zone_id),
            )
            canvas.tag_raise(entry.win_id)

    def set_zones_visible(self, visible: bool) -> None:
        self._zones_visible = visible
        if visible:
            self.reposition()
        else:
            for entry in self._zone_windows:
                if entry.win_id is not None:
                    self.canvas.delete(entry.win_id)
                    entry.win_id = None

    @property
    def zones_visible(self) -> bool:
        return self._zones_visible


class OverlayZoneMount:
    """Percent-positioned zone hosts on a transparent CTk overlay — no canvas create_window flicker."""

    def __init__(self, overlay: ctk.CTkFrame, page_id: str) -> None:
        self.overlay = overlay
        self.page_id = page_id
        self._hosts: dict[str, ctk.CTkFrame] = {}

    def _zone_spec(self, zone_id: str) -> dict[str, Any]:
        zones = zone_index(self.page_id)
        if zone_id not in zones:
            raise KeyError(f"unknown zone: {zone_id}")
        return zones[zone_id]

    def get_zone_host(self, zone_id: str) -> ctk.CTkFrame:
        if zone_id not in self._hosts:
            spec = self._zone_spec(zone_id)
            ax = float(spec["anchor"]["x"])
            ay = float(spec["anchor"]["y"])
            zw = float(spec["size"]["w"])
            zh = float(spec["size"]["h"])
            host = ctk.CTkFrame(self.overlay, fg_color="transparent", corner_radius=0)
            host.place(relx=ax, rely=ay, relwidth=zw, relheight=zh, anchor="center")
            self._hosts[zone_id] = host
        return self._hosts[zone_id]

    def reposition(self) -> None:
        for zone_id, host in self._hosts.items():
            spec = self._zone_spec(zone_id)
            ax = float(spec["anchor"]["x"])
            ay = float(spec["anchor"]["y"])
            zw = float(spec["size"]["w"])
            zh = float(spec["size"]["h"])
            host.place(relx=ax, rely=ay, relwidth=zw, relheight=zh, anchor="center")

    def set_zones_visible(self, visible: bool) -> None:
        if visible:
            self.reposition()
        else:
            for host in self._hosts.values():
                host.place_forget()
