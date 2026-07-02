"""Risk area #4 - SQLite connections are released, never leaked.

Opens many connections to the same DB file (including from multiple threads) and
verifies that an open-connection counter returns to zero once each ``with`` block
exits, and that a closed connection can no longer be used.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from ai_command_center.db.connection import connect


class ConnectionTracker:
    """Counts currently-open connections opened through :meth:`open`."""

    def __init__(self) -> None:
        self._open = 0
        self._peak = 0
        self._lock = threading.Lock()

    @property
    def open_count(self) -> int:
        with self._lock:
            return self._open

    @property
    def peak(self) -> int:
        with self._lock:
            return self._peak

    @contextmanager
    def open(self, db_path: Path):
        conn = connect(db_path)
        with self._lock:
            self._open += 1
            self._peak = max(self._peak, self._open)
        try:
            yield conn
        finally:
            conn.close()
            with self._lock:
                self._open -= 1


def test_single_threaded_connections_all_close(temp_db_path: Path) -> None:
    tracker = ConnectionTracker()
    for _ in range(25):
        with tracker.open(temp_db_path) as conn:
            conn.execute("SELECT 1").fetchone()
    assert tracker.peak >= 1, "tracker never observed an open connection"
    assert tracker.open_count == 0, (
        f"connection leak: {tracker.open_count} still open after all blocks exited"
    )


def test_multithreaded_connections_all_close(temp_db_path: Path) -> None:
    tracker = ConnectionTracker()
    errors: list[BaseException] = []
    barrier = threading.Barrier(8)

    def worker() -> None:
        try:
            barrier.wait(timeout=10)
            for _ in range(20):
                with tracker.open(temp_db_path) as conn:
                    conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"worker thread(s) raised: {errors}"
    assert all(not t.is_alive() for t in threads), "a worker thread hung"
    assert tracker.peak >= 2, "expected concurrent connections to overlap"
    assert tracker.open_count == 0, (
        f"connection leak across threads: {tracker.open_count} still open"
    )


def test_closed_connection_is_unusable(temp_db_path: Path) -> None:
    conn = connect(temp_db_path)
    conn.execute("SELECT 1").fetchone()
    conn.close()
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")
