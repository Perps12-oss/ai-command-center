"""Risk area #4 - memory stability under a sustained session (soak test).

Simulates a user session: repeatedly fires the hotkey / routes commands, issues
RAG-style queries and streams stub LLM responses through the real EventBus +
AppStateStore. Samples RSS with ``psutil`` and asserts the net growth stays
below a threshold after ``gc.collect()``.

Defaults are short so CI stays fast. Tune with environment variables::

    AICC_SOAK_SECONDS=1800   # full 30-minute soak
    AICC_SOAK_MAX_GROWTH_MB=50
"""

from __future__ import annotations

import gc
import os
import time

import pytest

psutil = pytest.importorskip("psutil")

from ai_command_center.core.app_state import AppStateStore  # noqa: E402
from ai_command_center.core.context_manager import ContextBundle  # noqa: E402
from ai_command_center.core.events.topics import (  # noqa: E402
    APP_PHASE,
    EXECUTION_AUTHORITY_DECISION,
    SYSTEM_SNAPSHOT,
)
from ai_command_center.services.ollama_service import StubOllamaService  # noqa: E402
from tests.support import RecordingEventBus  # noqa: E402

pytestmark = pytest.mark.slow

_SOAK_SECONDS = float(os.environ.get("AICC_SOAK_SECONDS", "6"))
_MAX_GROWTH_MB = float(os.environ.get("AICC_SOAK_MAX_GROWTH_MB", "50"))
_SAMPLE_EVERY = float(os.environ.get("AICC_SOAK_SAMPLE_SECONDS", "1"))


def _one_interaction(bus: RecordingEventBus, ollama: StubOllamaService, n: int) -> None:
    # hotkey toggles a phase
    bus.publish(APP_PHASE, {"phase": "overlay" if n % 2 else "idle"}, source="hotkey")
    # an authority decision for a RAG-style query
    bus.publish(
        EXECUTION_AUTHORITY_DECISION,
        {"text": f"note: query {n}", "capability": "notes.search"},
        source="execution_authority",
    )
    # a system snapshot tick
    bus.publish(
        SYSTEM_SNAPSHOT,
        {"cpu_percent": 5.0, "ram_percent": 40.0, "ollama_online": True},
        source="observer",
    )
    # a streamed stub completion
    bundle = ContextBundle(prompt=f"q{n}", sources=("note",), token_estimate=8)
    ollama.stream_chat(bundle, model="fake-model")
    # keep the recorded-event log bounded so the *harness* itself doesn't leak
    bus.clear()


def test_memory_stays_bounded_during_session() -> None:
    proc = psutil.Process()
    bus = RecordingEventBus()
    store = AppStateStore(bus)
    ollama = StubOllamaService(bus)
    ollama.start()

    gc.collect()
    baseline_mb = proc.memory_info().rss / (1024 * 1024)
    samples: list[float] = [baseline_mb]

    deadline = time.monotonic() + _SOAK_SECONDS
    next_sample = time.monotonic() + _SAMPLE_EVERY
    n = 0
    try:
        while time.monotonic() < deadline:
            _one_interaction(bus, ollama, n)
            n += 1
            now = time.monotonic()
            if now >= next_sample:
                samples.append(proc.memory_info().rss / (1024 * 1024))
                next_sample = now + _SAMPLE_EVERY
    finally:
        ollama.stop()
        store.close()

    gc.collect()
    final_mb = proc.memory_info().rss / (1024 * 1024)
    growth = final_mb - baseline_mb

    assert n > 0, "soak loop never executed an interaction"
    assert growth < _MAX_GROWTH_MB, (
        f"RSS grew {growth:.1f} MB over {_SOAK_SECONDS:.0f}s / {n} interactions "
        f"(limit {_MAX_GROWTH_MB:.0f} MB). Samples MB: "
        f"{[round(s, 1) for s in samples]}"
    )
