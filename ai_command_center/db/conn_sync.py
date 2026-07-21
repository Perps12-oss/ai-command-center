"""Shared SQLite connection lock for EventBus worker threads.

Kept free of package imports so repositories can use the lock without
circular imports through ``db.connection`` → platform → repositories.

``sqlite3.Connection`` rejects arbitrary attributes and method reassignment on
CPython 3.12, so locks live in a side table keyed by ``id(conn)``.
"""

from __future__ import annotations

import sqlite3
import threading

# sqlite3.Connection is not weakref-able; drop entries explicitly on close if needed.
_LOCKS: dict[int, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def connection_lock(conn: sqlite3.Connection) -> threading.RLock:
    """Return the shared write lock for ``conn``.

    EventBus worker threads share one SQLite connection across repositories.
    Per-repository locks do not serialize access — multi-statement work must
    hold this lock for the whole critical section (execute through commit).
    """
    key = id(conn)
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


def drop_connection_lock(conn: sqlite3.Connection) -> None:
    """Release the side-table lock entry for a closed connection."""
    with _LOCKS_GUARD:
        _LOCKS.pop(id(conn), None)
