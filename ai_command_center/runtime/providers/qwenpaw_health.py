"""Shared QwenPaw sidecar health state (provider + service)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class QwenPawSidecarHealthState:
    enabled: bool = False
    reachable: bool = False
    auto_start: bool = False
    detail: str = "QwenPaw sidecar disabled"
    _lock: Lock = field(default_factory=Lock, repr=False)

    def snapshot(self) -> tuple[bool, bool, str]:
        with self._lock:
            return self.enabled, self.reachable, self.detail

    def update(
        self,
        *,
        enabled: bool | None = None,
        reachable: bool | None = None,
        auto_start: bool | None = None,
        detail: str | None = None,
    ) -> None:
        with self._lock:
            if enabled is not None:
                self.enabled = enabled
            if reachable is not None:
                self.reachable = reachable
            if auto_start is not None:
                self.auto_start = auto_start
            if detail is not None:
                self.detail = detail
