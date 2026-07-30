"""Mission Control layout preferences — density, favorites, widget order.

Persisted via SettingsSnapshot.mission_layout_prefs (schema v7).
UI-local progressive disclosure; does not invent domain contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Density(str, Enum):
    COMPACT = "compact"
    EXPANDED = "expanded"


DEFAULT_WIDGET_ORDER: tuple[str, ...] = (
    "status",
    "hero",
    "mid",
    "kpis",
    "lower",
    "dock",
    "system",
)


@dataclass
class LayoutPrefs:
    """Mutable layout preferences for Mission Control."""

    density: Density = Density.EXPANDED
    pinned_actions: list[str] = field(default_factory=list)
    favorites: list[str] = field(default_factory=list)
    recent_pages: list[str] = field(default_factory=list)
    show_advanced: bool = False
    widget_order: list[str] = field(default_factory=lambda: list(DEFAULT_WIDGET_ORDER))
    _max_recent: int = 8
    _max_favorites: int = 12
    _on_change: Any = None  # optional Callable[[LayoutPrefs], None]
    _on_debounce: Any = None  # optional Callable[[LayoutPrefs], None] for navigation
    _dirty: bool = False

    def bind_persist(self, on_change, *, on_debounce: Any = None) -> None:
        """Bind immediate persist (density/favorites/order) and optional debounce.

        ``on_debounce`` is used for high-frequency updates such as ``record_page``
        so sidebar navigation does not block the UI on SYNC_CRITICAL settings I/O.
        """
        self._on_change = on_change
        self._on_debounce = on_debounce

    def _persist(self) -> None:
        self._dirty = False
        if callable(self._on_change):
            try:
                self._on_change(self)
            except Exception:
                pass

    def _persist_debounced(self) -> None:
        """Mark dirty and schedule coalesced persist (or persist immediately)."""
        self._dirty = True
        if callable(self._on_debounce):
            try:
                self._on_debounce(self)
                return
            except Exception:
                pass
        # No scheduler available — skip per-click write; flush() later.

    def flush(self) -> None:
        """Write pending (e.g. recent_pages) changes if dirty."""
        if self._dirty:
            self._persist()

    def toggle_density(self) -> Density:
        self.density = (
            Density.COMPACT
            if self.density == Density.EXPANDED
            else Density.EXPANDED
        )
        self._persist()
        return self.density

    def is_compact(self) -> bool:
        return self.density == Density.COMPACT

    def pin_action(self, action_id: str) -> None:
        if action_id not in self.pinned_actions:
            self.pinned_actions.append(action_id)
            self._persist()

    def unpin_action(self, action_id: str) -> None:
        self.pinned_actions = [a for a in self.pinned_actions if a != action_id]
        self._persist()

    def toggle_favorite(self, view_id: str) -> bool:
        if view_id in self.favorites:
            self.favorites = [v for v in self.favorites if v != view_id]
            self._persist()
            return False
        if len(self.favorites) < self._max_favorites:
            self.favorites.append(view_id)
            self._persist()
        return True

    def record_page(self, view_id: str) -> None:
        """Update recent pages in memory; persist via debounce (not every click)."""
        self.recent_pages = [v for v in self.recent_pages if v != view_id]
        self.recent_pages.insert(0, view_id)
        self.recent_pages = self.recent_pages[: self._max_recent]
        self._persist_debounced()

    def toggle_advanced(self) -> bool:
        self.show_advanced = not self.show_advanced
        self._persist()
        return self.show_advanced

    def move_widget(self, widget_id: str, direction: int) -> list[str]:
        """Swap widget_id with neighbor (direction -1 up / +1 down)."""
        order = list(self.widget_order) or list(DEFAULT_WIDGET_ORDER)
        if widget_id not in order:
            order.append(widget_id)
        idx = order.index(widget_id)
        target = idx + int(direction)
        if target < 0 or target >= len(order):
            return order
        order[idx], order[target] = order[target], order[idx]
        self.widget_order = order
        self._persist()
        return order

    def to_dict(self) -> dict[str, Any]:
        return {
            "density": self.density.value,
            "pinned_actions": list(self.pinned_actions),
            "favorites": list(self.favorites),
            "recent_pages": list(self.recent_pages),
            "show_advanced": bool(self.show_advanced),
            "widget_order": list(self.widget_order) or list(DEFAULT_WIDGET_ORDER),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> LayoutPrefs:
        data = dict(raw or {})
        density_raw = str(data.get("density") or Density.EXPANDED.value).lower()
        density = Density.COMPACT if density_raw == Density.COMPACT.value else Density.EXPANDED
        order = [str(x) for x in (data.get("widget_order") or DEFAULT_WIDGET_ORDER) if str(x)]
        # Ensure all defaults present
        for wid in DEFAULT_WIDGET_ORDER:
            if wid not in order:
                order.append(wid)
        return cls(
            density=density,
            pinned_actions=[str(x) for x in data.get("pinned_actions") or []],
            favorites=[str(x) for x in data.get("favorites") or []],
            recent_pages=[str(x) for x in data.get("recent_pages") or []],
            show_advanced=bool(data.get("show_advanced", False)),
            widget_order=order,
        )
