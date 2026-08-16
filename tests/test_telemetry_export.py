"""Session telemetry export — file output, stats cache, shutdown wiring."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import CHAT_COMPLETE, UI_COMMAND
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
)
from ai_command_center.repositories.telemetry_repository import TelemetryRepository
from ai_command_center.telemetry import session_export as telemetry_export
from ai_command_center.telemetry.session_export import (
    STATS_CACHE_FILENAME,
    export_session,
    resolve_export_dir,
)
from ai_command_center.services.telemetry_service import TelemetryService


def _repo() -> TelemetryRepository:
    # Telemetry writes on a dedicated worker thread.
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    return TelemetryRepository(conn)


def _drain(repo: TelemetryRepository, session_id: str, expected: int) -> None:
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if len(repo.fetch_session(session_id)) >= expected:
            return
        time.sleep(0.02)
    raise AssertionError(f"telemetry rows never reached {expected}")


@pytest.fixture(autouse=True)
def _isolated_export_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "telemetry"
    monkeypatch.setenv(telemetry_export.ENV_EXPORT_DIR, str(target))
    monkeypatch.delenv(telemetry_export.ENV_EXPORT_ENABLED, raising=False)
    return target


def test_resolve_export_dir_honours_env_override(_isolated_export_dir: Path) -> None:
    assert resolve_export_dir() == _isolated_export_dir
    assert _isolated_export_dir.is_dir()


def test_export_session_writes_snapshot_and_stats_cache(_isolated_export_dir: Path) -> None:
    repo = _repo()
    repo.insert_many(
        [
            (UI_COMMAND, {"session_id": "s-1", "text": "Summarize"}, "2026-08-14T00:00:00+00:00"),
            (
                CHAT_COMPLETE,
                {"session_id": "s-1", "request_id": "r1", "model": "llama3.2:3b"},
                "2026-08-14T00:00:01+00:00",
            ),
            (
                CHAT_COMPLETE,
                {"session_id": "s-1", "request_id": "r2", "model": "qwen2.5:7b"},
                "2026-08-14T00:00:02+00:00",
            ),
        ]
    )

    path = export_session(repo, "s-1")

    assert path is not None and path.exists()
    export = json.loads(path.read_text(encoding="utf-8"))
    assert export["session_id"] == "s-1"
    assert export["event_count"] == 3
    assert export["models"] == ["llama3.2:3b", "qwen2.5:7b"]
    assert export["event_counts"][CHAT_COMPLETE] == 2
    assert "friction_score" in export["summary"]

    cache = json.loads((_isolated_export_dir / STATS_CACHE_FILENAME).read_text(encoding="utf-8"))
    assert cache["models"] == ["llama3.2:3b", "qwen2.5:7b"]
    assert cache["total_sessions"] == 1
    assert cache["total_events"] == 3
    assert cache["last_update"] == export["exported_at"]


def test_stats_cache_accumulates_across_sessions(_isolated_export_dir: Path) -> None:
    repo = _repo()
    repo.insert_many(
        [(CHAT_COMPLETE, {"session_id": "s-1", "model": "a"}, "2026-08-14T00:00:00+00:00")]
    )
    export_session(repo, "s-1")
    repo.insert_many(
        [(CHAT_COMPLETE, {"session_id": "s-2", "model": "b"}, "2026-08-14T01:00:00+00:00")]
    )
    export_session(repo, "s-2")

    cache = json.loads((_isolated_export_dir / STATS_CACHE_FILENAME).read_text(encoding="utf-8"))
    assert cache["models"] == ["a", "b"]
    assert cache["total_sessions"] == 2
    assert set(cache["sessions"]) == {"s-1", "s-2"}


def test_events_truncated_but_aggregates_cover_whole_session(
    _isolated_export_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(telemetry_export, "MAX_EXPORTED_EVENTS", 3)
    repo = _repo()
    repo.insert_many(
        [
            (UI_COMMAND, {"session_id": "s-1", "text": f"cmd-{i}"}, f"2026-08-14T00:00:0{i}+00:00")
            for i in range(6)
        ]
    )

    path = export_session(repo, "s-1")

    assert path is not None
    export = json.loads(path.read_text(encoding="utf-8"))
    assert export["event_count"] == 6
    assert export["events_truncated"] is True
    assert len(export["events"]) == 3
    assert export["event_counts"][UI_COMMAND] == 6
    # Most recent rows are the ones kept.
    assert export["events"][-1]["payload"]["text"] == "cmd-5"


def test_stats_cache_retains_only_recent_sessions(
    _isolated_export_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(telemetry_export, "MAX_CACHED_SESSIONS", 2)
    repo = _repo()
    for i in range(4):
        repo.insert_many(
            [(UI_COMMAND, {"session_id": f"s-{i}"}, f"2026-08-14T0{i}:00:00+00:00")]
        )
        export_session(repo, f"s-{i}")

    cache = json.loads((_isolated_export_dir / STATS_CACHE_FILENAME).read_text(encoding="utf-8"))
    assert set(cache["sessions"]) == {"s-2", "s-3"}
    assert cache["total_sessions"] == 2


def test_export_skipped_when_disabled(
    _isolated_export_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(telemetry_export.ENV_EXPORT_ENABLED, "0")
    repo = _repo()
    repo.insert_many([(UI_COMMAND, {"session_id": "s-1"}, "2026-08-14T00:00:00+00:00")])

    assert export_session(repo, "s-1") is None
    assert not (_isolated_export_dir / STATS_CACHE_FILENAME).exists()


def test_empty_session_produces_no_files(_isolated_export_dir: Path) -> None:
    assert export_session(_repo(), "s-none") is None
    assert not (_isolated_export_dir / STATS_CACHE_FILENAME).exists()


def test_broken_repo_does_not_raise(_isolated_export_dir: Path) -> None:
    class Broken:
        def fetch_session(self, session_id: str):  # noqa: ANN201 - test double
            raise RuntimeError("db gone")

    assert export_session(Broken(), "s-1") is None


def test_service_stop_exports_session(_isolated_export_dir: Path) -> None:
    bus = EventBus()
    repo = _repo()
    service = TelemetryService(bus, repo)
    service.start()
    try:
        bus.publish(UI_COMMAND, {"text": "Summarize"}, source="ui")
        _drain(repo, service.session_id, 1)
    finally:
        service.stop()

    path = _isolated_export_dir / f"session-{service.session_id}.json"
    assert path.exists()
    export = json.loads(path.read_text(encoding="utf-8"))
    assert export["event_count"] >= 1
    assert (_isolated_export_dir / STATS_CACHE_FILENAME).exists()


def test_claude_mirror_merges_stats_cache_without_clobbering(
    _isolated_export_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(telemetry_export.ENV_CLAUDE_MIRROR, "1")
    claude = tmp_path / ".claude"
    claude.mkdir()
    monkeypatch.setattr(telemetry_export, "resolve_claude_home", lambda: claude)
    stale = {
        "models": ["claude-sonnet-4-6"],
        "lastUpdate": "2026-05-08T00:00:00+00:00",
        "vendor_field": "keep-me",
    }
    (claude / telemetry_export.STATS_CACHE_FILENAME).write_text(
        json.dumps(stale), encoding="utf-8"
    )

    repo = _repo()
    repo.insert_many(
        [
            (
                CHAT_COMPLETE,
                {"session_id": "s-1", "model": "llama3.2:3b"},
                "2026-08-16T00:00:00+00:00",
            ),
            (
                CHAT_COMPLETE,
                {"session_id": "s-1", "model_name": "qwen2.5:7b"},
                "2026-08-16T00:00:01+00:00",
            ),
        ]
    )
    path = export_session(repo, "s-1")
    assert path is not None

    mirrored = claude / "telemetry" / "session-s-1.json"
    assert mirrored.exists()
    assert json.loads(mirrored.read_text(encoding="utf-8"))["session_id"] == "s-1"

    cache = json.loads((claude / telemetry_export.STATS_CACHE_FILENAME).read_text())
    assert cache["vendor_field"] == "keep-me"
    assert "claude-sonnet-4-6" in cache["models"]
    assert "llama3.2:3b" in cache["models"]
    assert "qwen2.5:7b" in cache["models"]
    assert cache["last_update"] == cache["lastUpdate"]
    assert cache["last_update"].startswith("2026-") or "T" in cache["last_update"]
    assert cache["acc"]["total_sessions"] == 1


def test_claude_mirror_skipped_when_disabled(
    _isolated_export_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(telemetry_export.ENV_CLAUDE_MIRROR, "0")
    monkeypatch.setattr(telemetry_export, "resolve_claude_home", lambda: tmp_path / ".claude")
    repo = _repo()
    repo.insert_many([(UI_COMMAND, {"session_id": "s-1"}, "2026-08-16T00:00:00+00:00")])
    export_session(repo, "s-1")
    assert not (tmp_path / ".claude" / "telemetry").exists()


def test_periodic_export_writes_before_stop(
    _isolated_export_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(telemetry_export.ENV_EXPORT_INTERVAL_S, "0.05")
    bus = EventBus()
    repo = _repo()
    service = TelemetryService(bus, repo)
    service.start()
    try:
        bus.publish(UI_COMMAND, {"text": "Summarize"}, source="ui")
        _drain(repo, service.session_id, 1)
        deadline = time.time() + 2.0
        path = _isolated_export_dir / f"session-{service.session_id}.json"
        while time.time() < deadline and not path.exists():
            time.sleep(0.02)
        assert path.exists(), "periodic export did not write before stop"
    finally:
        service.stop()
