"""Settings repository placeholder."""

from __future__ import annotations

from typing import Any


class SettingsRepository:
    """Simple in-memory repository for settings until SQLite wiring is added."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get_all(self) -> dict[str, Any]:
        return dict(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
