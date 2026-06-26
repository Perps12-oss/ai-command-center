"""Workspace OS core domain model (Reference Architecture v3.5, Part II).

These objects are passive data structures. They do not acquire telemetry, monitor
the clipboard, or track windows — acquisition belongs to later phases. A
``TelemetrySnapshot`` is a sensor reading handed in from outside; the
``WorkspaceContext`` is the primary architectural object built from it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    """Point-in-time observation of the operating environment (a sensor object)."""

    timestamp: float
    target_hwnd: int
    app_name: str
    window_title: str
    clipboard_text: str

    @classmethod
    def empty(cls, *, now: float | None = None) -> "TelemetrySnapshot":
        """Neutral snapshot for instant UI render before a reading arrives (A7)."""
        return cls(
            timestamp=now if now is not None else time.time(),
            target_hwnd=0,
            app_name="",
            window_title="",
            clipboard_text="",
        )


@dataclass
class WorkspaceContext:
    """Primary domain object — the current unit of ongoing work.

    Mutable so the UI can hydrate fields progressively (Runtime Lifecycle Phase 1)
    as evidence arrives, without reconstructing the object.
    """

    workspace_id: str
    title: str
    inferred_task: str
    active_snapshot: TelemetrySnapshot
    active_files: list[str] = field(default_factory=list)
    recent_snapshots: list[str] = field(default_factory=list)
    memory_refs: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkspaceLease:
    """Lease guarding workspace continuity across transient context loss (A6)."""

    workspace_id: str
    confidence: float
    expires_at: float

    def is_active(self, now: float | None = None) -> bool:
        return (now if now is not None else time.time()) < self.expires_at
