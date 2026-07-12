"""Shared pytest fixtures and path setup for the risk-area suite.

Importing this module guarantees the project root is importable (so both
``ai_command_center`` and ``tests.support`` resolve) regardless of the directory
pytest is launched from.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Some modules derive a runtime data dir from %APPDATA% (Windows). On non-Windows
# CI runners that variable is absent; provide a throwaway location so imports do
# not explode. Tests that touch SQLite always pass an explicit path anyway.
if not os.environ.get("APPDATA"):
    os.environ["APPDATA"] = tempfile.mkdtemp(prefix="aicc-appdata-")


def _module_available(name: str) -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


# Optional runtime deps that some *pre-existing* repo tests need (GUI / HTTP).
# When they are absent (e.g. a headless box without Tk), skip only the test
# modules that import them so the risk-area suite still runs via bare `pytest`.
_OPTIONAL_DEP_TRIGGERS = {
    "customtkinter": ("customtkinter", "ai_command_center.ui"),
    "tkinter": ("customtkinter", "ai_command_center.ui", "tkinter"),
    "aiohttp": ("aiohttp", "create_application", "ai_command_center.application"),
}
_MISSING_TRIGGER_STRINGS: tuple[str, ...] = tuple(
    {
        trigger
        for dep, triggers in _OPTIONAL_DEP_TRIGGERS.items()
        if not _module_available(dep)
        for trigger in triggers
    }
)


def pytest_ignore_collect(collection_path, config):  # type: ignore[no-untyped-def]
    """Skip pre-existing tests whose optional runtime deps are unavailable."""
    if not _MISSING_TRIGGER_STRINGS:
        return None
    path = Path(str(collection_path))
    if path.suffix != ".py" or not path.name.startswith("test_"):
        return None
    # Never skip the risk-area suite this PR adds.
    if path.parent.name == "tests" and path.name in _RISK_AREA_TESTS:
        return False
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if any(trigger in source for trigger in _MISSING_TRIGGER_STRINGS):
        return True
    return None


_RISK_AREA_TESTS = frozenset(
    {
        "test_arm64_binaries.py",
        "test_arm64_emulation_smoke.py",
        "test_architecture_lint.py",
        "test_state_immutability.py",
        "test_eventbus_concurrency.py",
        "test_prompt_injection_sandbox.py",
        "test_path_traversal.py",
        "test_memory_soak.py",
        "test_sqlite_connection_cleanup.py",
        "test_indexing_tracemalloc.py",
        "test_service_lifecycle_chaos.py",
        "test_service_unload_timeout.py",
        "test_service_resource_lock.py",
    }
)


def pytest_configure(config: pytest.Config) -> None:
    # Markers are also declared in pytest.ini; re-declare defensively so the
    # suite works even if invoked with a different ini.
    for marker in (
        "slow: long-running soak/chaos tests",
        "windows: requires a real Windows host",
        "arm64: requires native Windows ARM64",
        "security: prompt-injection / sandbox / path-traversal hardening tests",
    ):
        config.addinivalue_line("markers", marker)


@pytest.fixture
def event_bus():
    """A recording EventBus that logs every published event (thread-safe)."""
    from tests.support import RecordingEventBus

    return RecordingEventBus()


@pytest.fixture
def mock_event_bus():
    """A minimal mock EventBus for operator tests.

    Returns a simple object that implements publish() for testing
    components that don't need full EventBus functionality.
    """
    from dataclasses import dataclass, field

    @dataclass
    class MockEvent:
        topic: str
        payload: dict = field(default_factory=dict)
        source: str = "test"

    class MockEventBus:
        def __init__(self):
            self.published: list[MockEvent] = []

        def publish(self, topic: str, payload: dict | None = None, *, source: str = "test"):
            self.published.append(MockEvent(topic=topic, payload=payload or {}, source=source))

        def subscribe(self, topic: str, handler):
            return lambda: None  # No-op unsubscribe

    return MockEventBus()


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Path to a fresh, bootstrapped SQLite DB file (schema applied)."""
    from ai_command_center.db.connection import connect, init_database

    db_path = tmp_path / "app.db"
    conn = connect(db_path)
    try:
        init_database(conn)
    finally:
        conn.close()
    return db_path


@pytest.fixture
def temp_db_conn(temp_db_path: Path):
    """An open connection to a bootstrapped SQLite DB, closed on teardown."""
    conn = sqlite3.connect(temp_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """An empty directory that stands in for an Obsidian vault root."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault
