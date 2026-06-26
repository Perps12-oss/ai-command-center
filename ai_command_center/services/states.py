"""Service lifecycle states."""

from __future__ import annotations

from enum import Enum


class ServiceState(str, Enum):
    """Canonical service lifecycle states (AGENTS.md v4)."""

    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    ERROR = "error"
    STOPPING = "stopping"
