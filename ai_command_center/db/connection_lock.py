"""Per-connection mutex for shared sqlite3 handles across threads."""

from __future__ import annotations

import sqlite3
import threading

_LOCKS: dict[int, threading.RLock] = {}
_REGISTRY = threading.Lock()


def connection_lock(conn: sqlite3.Connection) -> threading.RLock:
    """Return a per-connection reentrant mutex for shared sqlite3 handles."""
    key = id(conn)
    with _REGISTRY:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


def release_connection_lock(conn: sqlite3.Connection) -> None:
    """Drop the mutex for a closed connection (optional hygiene)."""
    with _REGISTRY:
        _LOCKS.pop(id(conn), None)


__all__ = ["connection_lock", "release_connection_lock"]
