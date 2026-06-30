"""Risk area #5 - services must release OS resource locks on teardown.

A service acquires an exclusive lock on a file in the vault directory. The test
verifies that:

* while the service is loaded, an independent probe cannot acquire the lock;
* after the service is unloaded (the lifecycle analogue of "hibernate"), the
  lock is released and the probe succeeds;
* a service whose teardown hangs keeps the lock - demonstrating the leak the
  watchdog timeout is meant to surface (so the manager can force-close it).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.services.base import BaseService
from ai_command_center.services.states import ServiceState
from tests.support import run_with_timeout


def _try_acquire_exclusive(path: Path) -> bool:
    """Attempt a non-blocking exclusive lock on ``path``; release immediately.

    Returns True if the lock was acquired (i.e. nobody else holds it).
    """
    if sys.platform == "win32":
        import msvcrt

        try:
            fd = os.open(str(path), os.O_RDWR | os.O_CREAT)
        except OSError:
            return False
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            return True
        except OSError:
            return False
        finally:
            os.close(fd)
    else:
        import fcntl

        fd = os.open(str(path), os.O_RDWR | os.O_CREAT)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return True
        except OSError:
            return False
        finally:
            os.close(fd)


class LockingService(BaseService):
    """Holds an exclusive lock on ``<vault>/.aicc.lock`` while loaded."""

    name = "vault_lock"

    def __init__(self, bus: EventBus, vault: Path, *, hang_on_unload: bool = False) -> None:
        super().__init__(bus)
        self._lock_path = vault / ".aicc.lock"
        self._fd: int | None = None
        self._hang = hang_on_unload
        import threading

        self._release_gate = threading.Event()

    def _on_load(self) -> None:
        self._fd = os.open(str(self._lock_path), os.O_RDWR | os.O_CREAT)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._fd, fcntl.LOCK_EX)

    def _on_unload(self) -> None:
        if self._hang:
            self._release_gate.wait()
        self._release_lock()

    def _release_lock(self) -> None:
        if self._fd is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                try:
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl

                fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None

    def force_release(self) -> None:
        self._release_gate.set()
        self._release_lock()


def test_lock_released_after_unload(temp_vault: Path) -> None:
    bus = EventBus()
    service = LockingService(bus, temp_vault)
    lock_path = temp_vault / ".aicc.lock"

    service.load()
    assert service.state == ServiceState.READY
    assert not _try_acquire_exclusive(lock_path), (
        "lock should be held by the loaded service"
    )

    run_with_timeout(service.unload, timeout=2.0)
    assert service.state == ServiceState.STOPPED
    assert _try_acquire_exclusive(lock_path), (
        "service must release its vault lock on unload"
    )


def test_hanging_service_keeps_lock_until_forced(temp_vault: Path) -> None:
    from tests.support.timeouts import TimeoutError as WatchdogTimeoutError

    bus = EventBus()
    service = LockingService(bus, temp_vault, hang_on_unload=True)
    lock_path = temp_vault / ".aicc.lock"
    service.load()

    try:
        with pytest.raises((WatchdogTimeoutError, TimeoutError)):
            run_with_timeout(service.unload, timeout=1.0)
        # The deadlocked teardown still holds the lock - this is the leak the
        # manager must force-close after a timeout.
        assert not _try_acquire_exclusive(lock_path), (
            "hung service unexpectedly released its lock"
        )
    finally:
        service.force_release()

    # After a forced release, the resource is recoverable.
    assert _try_acquire_exclusive(lock_path), "lock not recoverable after force release"
