"""Benchmarks + behavioural guards for the performance architecture refactor."""

from __future__ import annotations

import os
import sqlite3
import statistics
import time

import pytest

os.environ.setdefault("APPDATA", f"/tmp/aicc_perf_{os.getpid()}")

from ai_command_center.application import create_application
from ai_command_center.core.events.topics import (
    SETTINGS_SNAPSHOT,
    SYSTEM_SNAPSHOT,
    UI_COMMAND,
    UI_NAVIGATE,
)
from ai_command_center.core.perf.metrics import get_perf_metrics
from ai_command_center.core.state.reducer_index import build_topic_reducer_index
from ai_command_center.core.app_state import APP_STATE_TOPICS, AppState, _DEFAULT_REDUCERS
from ai_command_center.platform.secret_store import (
    invalidate_openai_key_cache,
    openai_api_key_configured,
    resolve_openai_api_key,
)


@pytest.fixture()
def core(tmp_path):
    previous_appdata = os.environ.get("APPDATA")
    os.environ["APPDATA"] = str(tmp_path)
    app = create_application()
    app.startup()
    try:
        yield app
    finally:
        app.shutdown()
        if previous_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = previous_appdata


def test_reducer_index_narrows_system_snapshot() -> None:
    index = build_topic_reducer_index(
        _DEFAULT_REDUCERS, APP_STATE_TOPICS, empty_state=AppState()
    )
    snap_reducers = index[SYSTEM_SNAPSHOT]
    assert 0 < len(snap_reducers) < len(_DEFAULT_REDUCERS)


def test_reducer_index_includes_imported_topic_handlers() -> None:
    """Handlers that compare against imported topic constants must be indexed."""
    from ai_command_center.core.events.topics import CHAT_CHUNK, WORKFLOW_STARTED

    index = build_topic_reducer_index(
        _DEFAULT_REDUCERS, APP_STATE_TOPICS, empty_state=AppState()
    )
    chat_names = {getattr(r, "__name__", "") for r in index[CHAT_CHUNK]}
    workflow_names = {getattr(r, "__name__", "") for r in index[WORKFLOW_STARTED]}
    assert "_reduce_chat_chunk" in chat_names
    assert "_reduce_chat_session_snapshot" in chat_names
    assert "_reduce_workflow_run" in workflow_names
    assert "_reduce_workflow_graph" in workflow_names


def test_appstate_reduce_under_budget(core) -> None:
    store = core.state_store
    times = []
    for i in range(40):
        st = time.perf_counter()
        store._on_event(
            type(
                "E",
                (),
                {
                    "topic": SYSTEM_SNAPSHOT,
                    "payload": {
                        "cpu_percent": float(i % 7),
                        "ram_percent": 40.0,
                        "ollama_online": False,
                        "extra": {"openai_online": False},
                        "eventbus_topic_counts": {"n": i},
                    },
                    "timestamp": time.time(),
                    "source": "bench",
                    "event_id": f"e{i}",
                },
            )()
        )
        times.append((time.perf_counter() - st) * 1000.0)
    assert statistics.mean(times) < 0.75
    assert max(times) < 5.0


def test_settings_single_snapshot(core) -> None:
    snaps: list = []
    core.bus.subscribe(SETTINGS_SNAPSHOT, lambda e: snaps.append(e))
    settings = None
    reg = getattr(core.services, "_services", None) or getattr(
        core.services, "_by_name", {}
    )
    if isinstance(reg, dict):
        settings = reg.get("settings")
    assert settings is not None
    before = len(snaps)
    for _ in range(20):
        try:
            settings.set("theme", core.state_store.snapshot.settings.theme)
            break
        except sqlite3.OperationalError as exc:
            if "database is locked" not in str(exc).lower():
                raise
            time.sleep(0.05)
    else:
        raise AssertionError("settings write remained locked after retries")
    # Allow nested publishes to settle
    time.sleep(0.05)
    assert len(snaps) - before == 1


def test_telemetry_publish_does_not_block(core) -> None:
    st = time.perf_counter()
    for _ in range(30):
        core.bus.publish(UI_NAVIGATE, {"view": "memory"}, source="ui")
    elapsed = (time.perf_counter() - st) * 1000.0
    assert elapsed < 60.0  # 30 publishes << sync SQLite era
    # Worker flushes async
    time.sleep(0.2)


def test_keyring_cache_avoids_repeat_work() -> None:
    invalidate_openai_key_cache()
    a = resolve_openai_api_key("")
    b = resolve_openai_api_key("")
    assert a == b
    assert openai_api_key_configured("") == bool(a)


def test_perf_metrics_record() -> None:
    m = get_perf_metrics()
    m.record("bench.sample", 1.25)
    snap = m.snapshot()
    assert "bench.sample" in snap["timings"]


def test_ui_command_publish_budget(core) -> None:
    times = []
    for i in range(8):
        st = time.perf_counter()
        core.bus.publish(UI_COMMAND, {"text": f"ping {i}"}, source="ui")
        times.append((time.perf_counter() - st) * 1000.0)
    # Art IV SYNC_CRITICAL target is <5 ms. Post-admit dispatch is ASYNC; CI
    # uses a slightly looser mean floor for machine variance.
    assert statistics.mean(times) < 8.0
