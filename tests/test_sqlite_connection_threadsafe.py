"""Thread-safety for the shared SQLite connection used by EventBus workers."""

from __future__ import annotations

import threading
from pathlib import Path

from ai_command_center.db.conn_sync import connection_lock
from ai_command_center.db.connection import connect, init_database


def test_concurrent_commits_on_shared_connection(tmp_path: Path) -> None:
    conn = init_database(connect(tmp_path / "race.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS race_t (x INTEGER)")
    conn.commit()
    errors: list[BaseException] = []

    def worker(n: int) -> None:
        try:
            for i in range(100):
                with connection_lock(conn):
                    conn.execute("INSERT INTO race_t VALUES (?)", (n * 1000 + i,))
                    conn.commit()
        except BaseException as exc:  # noqa: BLE001 — collect any thread failure
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    count = conn.execute("SELECT COUNT(*) AS n FROM race_t").fetchone()["n"]
    assert int(count) == 800


def test_memory_path_connect_skips_mkdir_for_in_memory() -> None:
    conn = connect(Path(":memory:"))
    try:
        with connection_lock(conn):
            conn.execute("CREATE TABLE t (x)")
            conn.commit()
            conn.execute("INSERT INTO t VALUES (1)")
            conn.commit()
        assert conn.execute("SELECT x FROM t").fetchone()["x"] == 1
    finally:
        conn.close()
