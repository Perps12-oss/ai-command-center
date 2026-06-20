#!/usr/bin/env python3
"""Knowledge access gate — note index, clipboard intent, error surfacing."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Knowledge Access Gate ===")
    failures: list[str] = []

    from ai_command_center.core.clipboard_intent import wants_clipboard
    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.db.note_repository import NoteRepository
    from ai_command_center.services.chat_handler_service import ChatHandlerService
    from ai_command_center.services.ollama_http_service import OllamaHttpService

    clip_cases = (
        ("Summarize this clipboard", True),
        ("Summarize clipboad", True),
        ("Summarize this clip", True),
        ("hello world", False),
    )
    for text, expected in clip_cases:
        got = wants_clipboard(text)
        if got != expected:
            failures.append(f"wants_clipboard({text!r}) = {got}, expected {expected}")

    mgr = ContextManager(max_context_tokens=1000)
    history = [("user", "old question"), ("assistant", "old answer")] * 5
    bundle = mgr.build_context(
        "Summarize this clipboard",
        clipboard="fresh clip text",
        conversation_history=history,
        clipboard_intent=True,
    )
    if "conversation_history" in bundle.sources:
        failures.append("clipboard_intent should omit conversation history")
    if "clipboard" not in bundle.sources:
        failures.append("clipboard_intent missing clipboard source")

    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp) / "vault"
        vault.mkdir()
        (vault / "stress-test.md").write_text("# Stress test\n\ntest content here\n", encoding="utf-8")
        (vault / "clipboard-tips.md").write_text("# Tips\nclipboard tips\n", encoding="utf-8")
        (vault / "settings-guide.md").write_text("# Settings\nsettings guide\n", encoding="utf-8")

        db_path = Path(tmp) / "notes.db"
        conn = connect(db_path)
        init_database(conn)
        repo = NoteRepository(conn)
        for md in vault.glob("*.md"):
            rel = md.name
            body = md.read_text(encoding="utf-8")
            repo.upsert(rel, md.stem, body, md.stat().st_mtime)

        if repo.count_indexed() != 3:
            failures.append(
                f"expected 3 indexed notes, got {repo.count_indexed()}"
            )
        hits = repo.search("test")
        if not hits:
            failures.append('search("test") returned no hits')
        conn.close()

        # Simulate stale trigger schema migration
        legacy = connect(Path(tmp) / "legacy.db")
        init_database(legacy)
        legacy.executescript(
            """
            CREATE TRIGGER note_index_ai AFTER INSERT ON note_index BEGIN
                INSERT INTO note_fts(rowid, title, body)
                VALUES (new.rowid, new.title, new.body);
            END;
            """
        )
        legacy.commit()
        init_database(legacy)
        triggers = legacy.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='note_index'"
        ).fetchall()
        if triggers:
            failures.append("migration left stale note_index triggers")
        legacy_repo = NoteRepository(legacy)
        legacy_repo.upsert("a.md", "A", "one", 1.0)
        legacy_repo.upsert("b.md", "B", "two test", 2.0)
        if legacy_repo.count_indexed() != 2:
            failures.append("post-migration upsert failed to index both notes")
        legacy.close()

    bus = EventBus(debug_mode=True)
    errors: list[dict] = []
    bus.subscribe("chat.error", lambda e: errors.append(dict(e.payload)))
    handler = ChatHandlerService(bus, ContextManager(), OllamaHttpService(bus))
    handler.load()
    bus.publish(
        "command.routed",
        {
            "intent": "chat",
            "status": "pending",
            "args": {"prompt": "Summarize clipboad", "clipboard": ""},
        },
        source="command_router",
    )
    time.sleep(0.05)
    handler.unload()
    if not errors:
        failures.append("typo clip intent with empty clipboard should emit chat.error")

    app_py = (PROJECT_ROOT / "ai_command_center" / "ui" / "app.py").read_text(
        encoding="utf-8"
    )
    if "wants_clipboard" not in app_py:
        failures.append("app.py must use wants_clipboard")
    err_block = app_py.split("def _on_chat_error", 1)[-1].split("def _on_ollama_status", 1)[0]
    if 'self._navigate("chat")' not in err_block:
        failures.append("chat.error handler must navigate to chat view")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: knowledge_access — index, clipboard intent, errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
