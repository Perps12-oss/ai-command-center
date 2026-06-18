"""Service lifecycle states."""

from __future__ import annotations

from enum import Enum


class ServiceState(str, Enum):
    OFF = "off"
    IDLE = "idle"
    ACTIVE = "active"
    HIBERNATED = "hibernated"
