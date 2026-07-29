"""Mission Control layout preferences — UI-local progressive disclosure.

Density and pin state are renderer preferences. They do not alter AppState
or domain contracts. Favorites/recents are in-session navigation aids.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Density(str, Enum):
    COMPACT = "compact"
    EXPANDED = "expanded"


@dataclass
class LayoutPrefs:
    """Mutable UI-local layout preferences for Mission Control."""

    density: Density = Density.EXPANDED
    pinned_actions: list[str] = field(default_factory=list)
    favorites: list[str] = field(default_factory=list)
    recent_pages: list[str] = field(default_factory=list)
    show_advanced: bool = False
    _max_recent: int = 8
    _max_favorites: int = 12

    def toggle_density(self) -> Density:
        self.density = (
            Density.COMPACT
            if self.density == Density.EXPANDED
            else Density.EXPANDED
        )
        return self.density

    def is_compact(self) -> bool:
        return self.density == Density.COMPACT

    def pin_action(self, action_id: str) -> None:
        if action_id not in self.pinned_actions:
            self.pinned_actions.append(action_id)

    def unpin_action(self, action_id: str) -> None:
        self.pinned_actions = [a for a in self.pinned_actions if a != action_id]

    def toggle_favorite(self, view_id: str) -> bool:
        if view_id in self.favorites:
            self.favorites = [v for v in self.favorites if v != view_id]
            return False
        if len(self.favorites) < self._max_favorites:
            self.favorites.append(view_id)
        return True

    def record_page(self, view_id: str) -> None:
        self.recent_pages = [v for v in self.recent_pages if v != view_id]
        self.recent_pages.insert(0, view_id)
        self.recent_pages = self.recent_pages[: self._max_recent]

    def toggle_advanced(self) -> bool:
        self.show_advanced = not self.show_advanced
        return self.show_advanced
