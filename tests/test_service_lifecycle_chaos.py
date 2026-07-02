"""Risk area #5 - lifecycle chaos must not freeze the UI thread.

Background workers hammer ``load``/``unload`` on several services (each with a
small simulated I/O delay) while the main thread runs a heartbeat that stands in
for the Tkinter event loop. The test asserts the heartbeat never stalls beyond a
small bound (the UI stays responsive) and that services end in a consistent
state.
"""

from __future__ import annotations

import os
import random
import threading
import time

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_manager import ServiceManager
from ai_command_center.services.states import ServiceState
from tests.support import StubLifecycleService

pytestmark = pytest.mark.slow

_CHAOS_SECONDS = float(os.environ.get("AICC_CHAOS_SECONDS", "3"))
_MAX_HEARTBEAT_GAP = float(os.environ.get("AICC_CHAOS_MAX_GAP_SECONDS", "0.75"))


def test_chaotic_load_unload_keeps_main_thread_responsive() -> None:
    bus = EventBus()
    manager = ServiceManager(bus)
    services = [
        StubLifecycleService(bus, name=f"svc{i}", load_delay=0.01, unload_delay=0.01)
        for i in range(4)
    ]
    for svc in services:
        manager.register(svc)

    stop = threading.Event()
    errors: list[BaseException] = []

    def chaos() -> None:
        rng = random.Random(1234)
        try:
            while not stop.is_set():
                svc = rng.choice(services)
                if rng.random() < 0.5:
                    svc.load()
                else:
                    svc.unload()
                time.sleep(0.005)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    workers = [threading.Thread(target=chaos, name=f"chaos{i}") for i in range(3)]
    for w in workers:
        w.start()

    # Main-thread "Tkinter event loop": tick and record inter-tick gaps.
    gaps: list[float] = []
    last = time.monotonic()
    deadline = last + _CHAOS_SECONDS
    while time.monotonic() < deadline:
        time.sleep(0.02)
        now = time.monotonic()
        gaps.append(now - last)
        last = now

    stop.set()
    for w in workers:
        w.join(timeout=10)

    assert not errors, f"chaos workers raised: {errors}"
    assert all(not w.is_alive() for w in workers), "a chaos worker hung"

    max_gap = max(gaps) if gaps else 0.0
    assert max_gap < _MAX_HEARTBEAT_GAP, (
        f"main thread stalled for {max_gap:.3f}s (limit {_MAX_HEARTBEAT_GAP:.2f}s) "
        "- UI would have frozen"
    )

    # Drive everything to a clean stop and assert a consistent terminal state.
    manager.unload_all()
    for svc in services:
        assert svc.state in {ServiceState.STOPPED, ServiceState.READY}, (
            f"{svc.name} ended in unexpected state {svc.state}"
        )
