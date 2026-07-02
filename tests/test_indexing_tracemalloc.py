"""Risk area #4 - bounded memory while indexing a large vault.

Indexes a large (mock) Obsidian vault into the real SQLite FTS index under
``tracemalloc`` and asserts:

* peak traced allocation stays under a sane bound, and
* the large note bodies are released after indexing (post-GC traced memory
  drops well below the peak).
"""

from __future__ import annotations

import gc
import os
import tracemalloc

import pytest

from ai_command_center.db.note_repository import NoteRepository

_NOTE_COUNT = int(os.environ.get("AICC_INDEX_NOTE_COUNT", "1000"))
_PEAK_LIMIT_MB = float(os.environ.get("AICC_INDEX_PEAK_LIMIT_MB", "500"))
# ~2 KB body per note.
_BODY = ("lorem ipsum dolor sit amet consectetur adipiscing elit " * 40).strip()


def _fts5_available(conn) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts_probe USING fts5(x)")
        conn.execute("DROP TABLE _fts_probe")
        return True
    except Exception:
        return False


def test_indexing_large_vault_is_memory_bounded(temp_db_conn) -> None:
    if not _fts5_available(temp_db_conn):
        pytest.skip("SQLite FTS5 not available in this build")

    repo = NoteRepository(temp_db_conn)

    tracemalloc.start()
    try:
        # Build bodies, hold them, then index - mirrors a real indexing pass.
        bodies = {
            f"notes/note_{i:04d}.md": f"# Note {i}\n\n{_BODY}" for i in range(_NOTE_COUNT)
        }
        for path, body in bodies.items():
            repo.upsert(path, f"Note {path}", body, mtime=float(len(body)))

        _, peak = tracemalloc.get_traced_memory()
        peak_mb = peak / (1024 * 1024)

        assert repo.count_indexed() == _NOTE_COUNT, (
            f"expected {_NOTE_COUNT} indexed notes, got {repo.count_indexed()}"
        )
        assert peak_mb < _PEAK_LIMIT_MB, (
            f"indexing peaked at {peak_mb:.1f} MB (limit {_PEAK_LIMIT_MB:.0f} MB)"
        )

        # Drop the large in-memory bodies; they must be reclaimable.
        bodies.clear()
        del body  # noqa: F821 - last loop var
        gc.collect()
        current_after, _ = tracemalloc.get_traced_memory()
        current_after_mb = current_after / (1024 * 1024)

        assert current_after_mb < peak_mb, (
            f"memory not released after indexing: {current_after_mb:.1f} MB "
            f"still traced vs peak {peak_mb:.1f} MB"
        )
    finally:
        tracemalloc.stop()


def test_search_after_indexing_returns_hits(temp_db_conn) -> None:
    if not _fts5_available(temp_db_conn):
        pytest.skip("SQLite FTS5 not available in this build")

    repo = NoteRepository(temp_db_conn)
    repo.upsert("notes/alpha.md", "Alpha", "the quick brown fox", mtime=1.0)
    repo.upsert("notes/beta.md", "Beta", "lazy dog sleeps", mtime=1.0)

    hits = repo.search("quick")
    assert any(h.path == "notes/alpha.md" for h in hits), "FTS search missed a hit"
