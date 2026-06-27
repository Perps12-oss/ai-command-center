"""Thread-safety tests for the SQLite connection wrapper."""

from __future__ import annotations

import sqlite3
import threading

import pytest

from ai_command_center.db.connection import ThreadSafeConnection


@pytest.fixture
def safe_conn():
    raw = sqlite3.connect(":memory:", check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    conn = ThreadSafeConnection(raw)
    conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
    conn.commit()
    yield conn
    conn.close()


def test_thread_safe_connection_serializes_access(safe_conn: ThreadSafeConnection) -> None:
    """Multiple threads can safely use the same wrapped connection."""
    errors: list[Exception] = []

    def worker() -> None:
        try:
            for i in range(50):
                safe_conn.execute("INSERT INTO t (x) VALUES (?)", (i,))
                safe_conn.commit()
                safe_conn.execute("SELECT COUNT(*) FROM t").fetchone()
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, f"Thread errors: {errors}"
    row = safe_conn.execute("SELECT COUNT(*) AS n FROM t").fetchone()
    assert row is not None
    assert int(row["n"]) == 4 * 50


def test_thread_safe_connection_forwards_attributes(safe_conn: ThreadSafeConnection) -> None:
    """Non-intercepted attributes are forwarded to the underlying connection."""
    assert safe_conn.in_transaction is False
