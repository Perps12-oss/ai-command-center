"""Per-handler EventBus dispatch metadata (R4c).

Services publish synchronously; heavy handlers may opt into ``async_queue`` so
invocation runs on the central ``event-dispatch`` thread when async adapters
are enabled. ``SYNC_CRITICAL`` topics always invoke every handler inline.

Feature flag: ``EVENTBUS_ASYNC_ADAPTERS=1`` (default off).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

Subscriber = Callable[[Any], None]


class HandlerDispatchMode(str, Enum):
    """How a single subscriber is invoked under R4c async adapters."""

    SYNC = "sync"
    """Always run on the current dispatch thread (default)."""
    ASYNC_QUEUE = "async_queue"
    """Defer to central dispatch queue when async adapters enabled."""
    ASYNCIO_BRIDGE = "asyncio_bridge"
    """Reserved for service-owned asyncio loops (R4c stub — treated as sync)."""


@dataclass(frozen=True, slots=True)
class HandlerRegistration:
    """Subscriber plus optional dispatch mode metadata."""

    handler: Subscriber
    dispatch_mode: HandlerDispatchMode = HandlerDispatchMode.SYNC


ASYNC_ADAPTERS_ENV = "EVENTBUS_ASYNC_ADAPTERS"
QUEUE_MAX_DEPTH_ENV = "EVENTBUS_QUEUE_MAX_DEPTH"
QUEUE_DROP_TELEMETRY_ENV = "EVENTBUS_QUEUE_DROP_TELEMETRY"


def async_adapters_enabled_from_env() -> bool:
    import os

    raw = os.environ.get(ASYNC_ADAPTERS_ENV, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def queue_max_depth_from_env() -> int:
    import os

    raw = os.environ.get(QUEUE_MAX_DEPTH_ENV, "").strip()
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


__all__ = [
    "ASYNC_ADAPTERS_ENV",
    "HandlerDispatchMode",
    "HandlerRegistration",
    "QUEUE_DROP_TELEMETRY_ENV",
    "QUEUE_MAX_DEPTH_ENV",
    "async_adapters_enabled_from_env",
    "queue_max_depth_from_env",
]
