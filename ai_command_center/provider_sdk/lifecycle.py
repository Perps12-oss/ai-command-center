"""Provider lifecycle state helpers."""

from __future__ import annotations

from enum import Enum


class ProviderLifecycleState(str, Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    CERTIFIED = "certified"
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISABLED = "disabled"
