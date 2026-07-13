"""Immutable AppState snapshot for the Service Registry.

Consolidates the flat AppState.services tuple into a typed snapshot that tracks
per-service lifecycle history, milestone counters, and a cross-service health trend.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class ServiceHistoryItem:
    """A single service state transition recorded for trend analysis."""

    state: str
    detail: str
    timestamp: float


_MAX_SERVICE_HISTORY = 20
_MAX_HEALTH_TREND = 50


@dataclass(frozen=True, slots=True)
class ServiceStateEntry:
    """Immutable projection of one service's lifecycle state and history."""

    name: str
    state: str
    detail: str
    history: tuple[ServiceHistoryItem, ...]
    started_count: int
    ready_count: int
    stopped_count: int
    error_count: int

    @property
    def last_transition(self) -> ServiceHistoryItem | None:
        return self.history[0] if self.history else None

    def with_state(
        self,
        state: str,
        detail: str,
        timestamp: float,
    ) -> "ServiceStateEntry":
        item = ServiceHistoryItem(state=state, detail=detail, timestamp=timestamp)
        history = (item,) + self.history
        if len(history) > _MAX_SERVICE_HISTORY:
            history = history[:_MAX_SERVICE_HISTORY]
        return replace(
            self,
            state=state,
            detail=detail,
            history=history,
        )

    def with_started(self, timestamp: float) -> "ServiceStateEntry":
        entry = self.with_state("started", "started", timestamp)
        return replace(entry, started_count=self.started_count + 1)

    def with_ready(self, timestamp: float) -> "ServiceStateEntry":
        entry = self.with_state("ready", "ready", timestamp)
        return replace(entry, ready_count=self.ready_count + 1)

    def with_stopped(self, timestamp: float) -> "ServiceStateEntry":
        entry = self.with_state("stopped", "stopped", timestamp)
        return replace(entry, stopped_count=self.stopped_count + 1)

    def with_error(self, detail: str, timestamp: float) -> "ServiceStateEntry":
        entry = self.with_state("error", detail, timestamp)
        return replace(entry, error_count=self.error_count + 1)


@dataclass(frozen=True, slots=True)
class ServiceRegistrySnapshot:
    """Immutable AppState projection of the service registry."""

    entries: tuple[ServiceStateEntry, ...]
    started_count: int
    ready_count: int
    stopped_count: int
    error_count: int
    health_trend: tuple[tuple[str, str, float], ...]

    def __init__(
        self,
        entries: tuple[ServiceStateEntry, ...] | None = None,
        started_count: int = 0,
        ready_count: int = 0,
        stopped_count: int = 0,
        error_count: int = 0,
        health_trend: tuple[tuple[str, str, float], ...] | None = None,
    ) -> None:
        object.__setattr__(self, "entries", entries or ())
        object.__setattr__(self, "started_count", started_count)
        object.__setattr__(self, "ready_count", ready_count)
        object.__setattr__(self, "stopped_count", stopped_count)
        object.__setattr__(self, "error_count", error_count)
        object.__setattr__(
            self, "health_trend", health_trend or ()
        )

    @property
    def total_services(self) -> int:
        return len(self.entries)

    @property
    def ready_count_live(self) -> int:
        return sum(1 for e in self.entries if e.state == "ready")

    @property
    def error_count_live(self) -> int:
        return sum(1 for e in self.entries if e.state == "error")

    @property
    def degraded_count_live(self) -> int:
        return sum(1 for e in self.entries if e.state == "degraded")

    @property
    def stopped_count_live(self) -> int:
        return sum(1 for e in self.entries if e.state == "stopped")

    @property
    def starting_count_live(self) -> int:
        return sum(1 for e in self.entries if e.state == "starting")

    def _entry_for(self, name: str) -> ServiceStateEntry:
        for entry in self.entries:
            if entry.name == name:
                return entry
        return ServiceStateEntry(
            name=name,
            state="unknown",
            detail="",
            history=(),
            started_count=0,
            ready_count=0,
            stopped_count=0,
            error_count=0,
        )

    def _updated_entries(
        self,
        name: str,
        entry: ServiceStateEntry,
    ) -> tuple[ServiceStateEntry, ...]:
        entries = tuple(
            sorted(
                tuple(e for e in self.entries if e.name != name) + (entry,),
                key=lambda e: e.name,
            )
        )
        return entries

    def _push_trend(
        self,
        name: str,
        state: str,
        timestamp: float,
    ) -> tuple[tuple[str, str, float], ...]:
        trend = ((name, state, timestamp),) + self.health_trend
        if len(trend) > _MAX_HEALTH_TREND:
            trend = trend[:_MAX_HEALTH_TREND]
        return trend

    def record_state_changed(
        self,
        name: str,
        state: str,
        detail: str,
        timestamp: float,
    ) -> "ServiceRegistrySnapshot":
        entry = self._entry_for(name).with_state(state, detail, timestamp)
        entries = self._updated_entries(name, entry)
        trend = self._push_trend(name, state, timestamp)
        return replace(
            self,
            entries=entries,
            health_trend=trend,
        )

    def record_started(
        self,
        name: str,
        timestamp: float,
    ) -> "ServiceRegistrySnapshot":
        entry = self._entry_for(name).with_started(timestamp)
        entries = self._updated_entries(name, entry)
        trend = self._push_trend(name, "started", timestamp)
        return replace(
            self,
            entries=entries,
            started_count=self.started_count + 1,
            health_trend=trend,
        )

    def record_ready(
        self,
        name: str,
        timestamp: float,
    ) -> "ServiceRegistrySnapshot":
        entry = self._entry_for(name).with_ready(timestamp)
        entries = self._updated_entries(name, entry)
        trend = self._push_trend(name, "ready", timestamp)
        return replace(
            self,
            entries=entries,
            ready_count=self.ready_count + 1,
            health_trend=trend,
        )

    def record_stopped(
        self,
        name: str,
        timestamp: float,
    ) -> "ServiceRegistrySnapshot":
        entry = self._entry_for(name).with_stopped(timestamp)
        entries = self._updated_entries(name, entry)
        trend = self._push_trend(name, "stopped", timestamp)
        return replace(
            self,
            entries=entries,
            stopped_count=self.stopped_count + 1,
            health_trend=trend,
        )

    def record_error(
        self,
        name: str,
        detail: str,
        timestamp: float,
    ) -> "ServiceRegistrySnapshot":
        entry = self._entry_for(name).with_error(detail, timestamp)
        entries = self._updated_entries(name, entry)
        trend = self._push_trend(name, "error", timestamp)
        return replace(
            self,
            entries=entries,
            error_count=self.error_count + 1,
            health_trend=trend,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "entries": [
                {
                    "name": e.name,
                    "state": e.state,
                    "detail": e.detail,
                    "history": [
                        {"state": h.state, "detail": h.detail, "timestamp": h.timestamp}
                        for h in e.history
                    ],
                    "started_count": e.started_count,
                    "ready_count": e.ready_count,
                    "stopped_count": e.stopped_count,
                    "error_count": e.error_count,
                }
                for e in self.entries
            ],
            "started_count": self.started_count,
            "ready_count": self.ready_count,
            "stopped_count": self.stopped_count,
            "error_count": self.error_count,
            "health_trend": [list(t) for t in self.health_trend],
        }
