"""Risk area #5 - a hanging unload must time out, not freeze the app.

The production ``ServiceManager`` calls ``service.stop()`` synchronously and has
no per-service timeout, so a deadlocked teardown would hang the caller forever.
These tests use the :func:`run_with_timeout` watchdog (the recommended wrapper)
to prove a hung unload is detected as a ``TimeoutError`` while the calling thread
stays responsive, and the offending service is observable as "unresponsive".
"""

from __future__ import annotations

import time

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_manager import ServiceManager
from ai_command_center.services.states import ServiceState
from tests.support import StubLifecycleService, run_with_timeout
from tests.support.timeouts import TimeoutError as WatchdogTimeoutError


def test_hanging_unload_raises_timeout_and_does_not_freeze_caller() -> None:
    bus = EventBus()
    manager = ServiceManager(bus)
    hung = StubLifecycleService(bus, name="hung", hang_on_unload=True)
    manager.register(hung)
    manager.load_all()
    assert hung.state == ServiceState.READY

    started = time.monotonic()
    try:
        with pytest.raises((WatchdogTimeoutError, TimeoutError)):
            run_with_timeout(manager.unload_all, timeout=1.0)
        elapsed = time.monotonic() - started

        # The caller regained control promptly (no freeze).
        assert elapsed < 3.0, f"caller blocked {elapsed:.2f}s despite 1s timeout"
        # The hung service is observably stuck mid-teardown ("unresponsive").
        assert hung.state == ServiceState.STOPPING, (
            f"hung service should be STOPPING, got {hung.state}"
        )
        assert hung.unload_count == 1, "unload should have been entered exactly once"
    finally:
        # Release the deadlock so the daemon watchdog thread can exit cleanly.
        hung.release()


def test_timeout_isolated_to_offending_service() -> None:
    """A healthy service unloads instantly under the same watchdog budget."""
    bus = EventBus()
    healthy = StubLifecycleService(bus, name="healthy")
    healthy.load()
    assert healthy.state == ServiceState.READY

    run_with_timeout(healthy.unload, timeout=1.0)
    assert healthy.state == ServiceState.STOPPED


def test_run_with_timeout_propagates_real_errors() -> None:
    def boom() -> None:
        raise ValueError("kaboom")

    with pytest.raises(ValueError, match="kaboom"):
        run_with_timeout(boom, timeout=1.0)
