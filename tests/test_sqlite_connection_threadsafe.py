"""P1-B: shared SQLite connection must not allow cross-thread commit steal."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from ai_command_center.db.conn_sync import GuardedConnection, connection_lock
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
    conn.close()


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


def test_thread_b_commit_cannot_steal_thread_a_partial(
    tmp_path: Path,
) -> None:
    """Regression for the verified P1-B failure mode.

    Thread A INSERT without commit; Thread B commit() must not make A's
    row durable.
    """
    db_path = tmp_path / "steal.db"
    conn = init_database(connect(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.commit()
    conn.execute("DELETE FROM t")
    conn.commit()

    a_inserted = threading.Event()
    b_done = threading.Event()
    log: list[str] = []

    def thread_a() -> None:
        # Leave an open transaction (no commit).
        conn.execute("INSERT INTO t (v) VALUES ('A_PARTIAL')")
        a_inserted.set()
        # Hold until B has attempted commit.
        assert b_done.wait(timeout=5.0)
        # Observer via separate connection.
        obs = connect(db_path)
        try:
            rows = [r[0] for r in obs.execute("SELECT v FROM t").fetchall()]
            log.append(f"after_B_commit_visible={rows}")
        finally:
            obs.close()
        conn.rollback()

    def thread_b() -> None:
        assert a_inserted.wait(timeout=5.0)
        # Give A a moment to keep txn open; then try to commit "our" work.
        time.sleep(0.02)
        # B's commit must block until A ends txn, OR if B acquires first it
        # must not see A's uncommitted work as its own to commit.
        # With GuardedConnection, B blocks on execute/commit until A releases.
        # Force B to attempt commit while A holds open txn — B blocks.
        started = time.time()
        conn.execute("INSERT INTO t (v) VALUES ('B_ONLY')")
        conn.commit()
        waited = time.time() - started
        log.append(f"B_waited={waited:.3f}")
        b_done.set()

    # Deadlock risk if A waits for B and B waits for A.
    # Redesign: A inserts and holds; B tries commit in parallel with timeout
    # proving B cannot complete while A holds; then A rollbacks; B proceeds.

    a_inserted.clear()
    b_blocked = threading.Event()
    a_release = threading.Event()
    results: dict[str, object] = {}

    def a2() -> None:
        conn.execute("INSERT INTO t (v) VALUES ('A_PARTIAL')")
        a_inserted.set()
        # Keep txn open until told to release.
        assert a_release.wait(timeout=5.0)
        conn.rollback()

    def b2() -> None:
        assert a_inserted.wait(timeout=5.0)
        b_blocked.set()
        # This must block until A rollbacks (lock held for open txn).
        t0 = time.time()
        conn.execute("INSERT INTO t (v) VALUES ('B_ONLY')")
        conn.commit()
        results["b_wait"] = time.time() - t0

    ta = threading.Thread(target=a2)
    tb = threading.Thread(target=b2)
    ta.start()
    tb.start()
    assert b_blocked.wait(timeout=5.0)
    time.sleep(0.15)
    # While A holds open txn, B must still be blocked (not finished).
    assert tb.is_alive(), "Thread B completed while A held an open transaction"
    # Separate observer must not see A_PARTIAL (uncommitted).
    obs = connect(db_path)
    try:
        visible = [r[0] for r in obs.execute("SELECT v FROM t").fetchall()]
    finally:
        obs.close()
    assert "A_PARTIAL" not in visible
    a_release.set()
    ta.join(timeout=5.0)
    tb.join(timeout=5.0)
    assert not ta.is_alive() and not tb.is_alive()
    assert float(results["b_wait"]) >= 0.1

    final = [r[0] for r in conn.execute("SELECT v FROM t ORDER BY id").fetchall()]
    assert "A_PARTIAL" not in final
    assert "B_ONLY" in final
    conn.close()


def test_connect_returns_guarded_connection(tmp_path: Path) -> None:
    conn = connect(tmp_path / "g.db")
    assert isinstance(conn, GuardedConnection)
    conn.close()


def test_unlocked_style_multi_statement_serialized(tmp_path: Path) -> None:
    """Former unlocked repository pattern is safe under GuardedConnection."""
    conn = init_database(connect(tmp_path / "multi.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS t (v TEXT)")
    conn.commit()
    errors: list[BaseException] = []

    def writer(tag: str) -> None:
        try:
            for i in range(50):
                # No explicit connection_lock — mimics Note/Entity repos.
                conn.execute("INSERT INTO t (v) VALUES (?)", (f"{tag}-{i}",))
                conn.commit()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(f"T{i}",)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    n = int(conn.execute("SELECT COUNT(*) AS n FROM t").fetchone()["n"])
    assert n == 300
    conn.close()
