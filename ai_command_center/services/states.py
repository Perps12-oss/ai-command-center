"""Service lifecycle states."""

from __future__ import annotations

from enum import Enum


class ServiceState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    ERROR = "error"
    STOPPING = "stopping"

    OFF = "stopped"
    IDLE = "idle"
    ACTIVE = "active"
    HIBERNATED = "stopped"
