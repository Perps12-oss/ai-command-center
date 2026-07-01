"""Reusable, deterministic test doubles and helpers for the risk-area suite.

Everything in this package is import-safe on any platform and performs no
network or GUI I/O, so the test suite stays fast and self-contained.
"""

from __future__ import annotations

from tests.support.mocks import (
    CountdownLatch,
    FakeOllamaClient,
    RecordingEventBus,
    StubLifecycleService,
)
from tests.support.sandbox import CommandSandbox, SecurityError
from tests.support.timeouts import TimeoutError as CallTimeoutError
from tests.support.timeouts import run_with_timeout

__all__ = [
    "CountdownLatch",
    "FakeOllamaClient",
    "RecordingEventBus",
    "StubLifecycleService",
    "CommandSandbox",
    "SecurityError",
    "CallTimeoutError",
    "run_with_timeout",
]
