"""Brain kernel state machine contract."""

from __future__ import annotations

from enum import Enum


class KernelState(str, Enum):
    BOOT = "boot"
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    PAUSED = "paused"
    RECOVERING = "recovering"
    SHUTDOWN = "shutdown"


ALLOWED_TRANSITIONS: dict[KernelState, frozenset[KernelState]] = {
    KernelState.BOOT: frozenset(
        {KernelState.RECOVERING, KernelState.IDLE, KernelState.SHUTDOWN}
    ),
    KernelState.RECOVERING: frozenset({KernelState.IDLE, KernelState.SHUTDOWN}),
    KernelState.IDLE: frozenset(
        {KernelState.PLANNING, KernelState.PAUSED, KernelState.SHUTDOWN}
    ),
    KernelState.PLANNING: frozenset(
        {
            KernelState.EXECUTING,
            KernelState.PAUSED,
            KernelState.IDLE,
            KernelState.SHUTDOWN,
        }
    ),
    KernelState.EXECUTING: frozenset(
        {
            KernelState.AWAITING_APPROVAL,
            KernelState.IDLE,
            KernelState.PAUSED,
            KernelState.SHUTDOWN,
        }
    ),
    KernelState.AWAITING_APPROVAL: frozenset(
        {
            KernelState.EXECUTING,
            KernelState.IDLE,
            KernelState.PAUSED,
            KernelState.SHUTDOWN,
        }
    ),
    KernelState.PAUSED: frozenset(
        {
            KernelState.IDLE,
            KernelState.PLANNING,
            KernelState.EXECUTING,
            KernelState.SHUTDOWN,
        }
    ),
    KernelState.SHUTDOWN: frozenset(),
}
