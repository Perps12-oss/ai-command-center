#!/usr/bin/env python3
"""Phase 3C gate — Obsidian FTS search, read/write, note injection via ContextManager."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _wait_for(events: list[str], topic: str, timeout: float = 5.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if topic in events:
            return True
        time.sleep(0.02)
    return False


def main() -> int:
    print("=== Phase 3C Gate Verification ===")
    failures: list[str] = []

    obsidian_path = PROJECT_ROOT / "ai_command_center" / "services" / "obsidian_service.py"
    if not obsidian_path.is_file():
        failures.append("obsidian_service.py missing")
    else:
        src = obsidian_path.read_text(encoding="utf-8")
        code_lines = [
            ln
            for ln in src.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        code = "\n".join(code_lines).lower()
        for banned in ("openai", "ollama", "sqlite-vec"):
            if banned in code:
                failures.append(f"obsidian_service must not reference {banned}")

    from ai_command_center.application import create_application

    app = create_application(debug_mode=True)
    if app.services.get("obsidian") is None:
        failures.append("obsidian service not registered")
    app.shutdown()

    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.repositories.note_repository import NoteRepository
    from ai_command_center.services.chat_handler_service import ChatHandlerService
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.obsidian_service import ObsidianService
    from ai_command_center.services.ollama_service import StubOllamaService

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        vault = tmp_path / "vault"
        vault.mkdir()
        note_file = vault / "meeting.md"
        note_file.write_text(
            "# Team Meeting\n\nDiscussed the product roadmap for Q3.\n",
            encoding="utf-8",
        )

        db = connect(tmp_path / "gate.db")
        init_database(db)
        repo = NoteRepository(db)

        bus = EventBus(debug_mode=True)
        events: list[str] = []
        payloads: dict[str, dict] = {}

        def tap(event) -> None:
            events.append(event.topic)
            payloads[event.topic] = dict(event.payload)

        bus.subscribe_all(tap)

        router = CommandRouterService(bus)
        obsidian = ObsidianService(bus, repo)
        ollama = StubOllamaService(bus)
        handler = ChatHandlerService(bus, ContextManager(), obsidian)
        for svc in (router, obsidian, ollama, handler):
            svc.load()

        bus.publish(
            "settings.snapshot",
            {"obsidian_vault_path": str(vault), "default_model": "llama3.2:3b"},
            source="test",
        )

        # Search — Phase 4A may return empty first, then refresh after index_complete
        events.clear()
        bus.publish("ui.command", {"text": "note:roadmap"}, source="test")
        end = time.time() + 15.0
        results = []
        while time.time() < end:
            if "note.search_results" in events:
                results = payloads.get("note.search_results", {}).get("results", [])
                if results:
                    break
            time.sleep(0.02)
        if not results:
            failures.append("note: query did not produce note.search_results with hits")
        else:
            paths = [r.get("path") for r in results]
            if "meeting.md" not in paths:
                failures.append(f"expected meeting.md in results, got {paths}")

        # Select note for injection
        bus.publish("note.select", {"path": "meeting.md"}, source="test")
        if not _wait_for(events, "note.selected"):
            failures.append("note.select did not produce note.selected")

        # Chat with injection — must pass through ContextManager
        events.clear()
        bus.publish("ui.command", {"text": "Summarize the meeting"}, source="test")
        if not _wait_for(events, "chat.started"):
            failures.append("chat did not start after note selection")
        else:
            sources = payloads.get("chat.started", {}).get("sources", [])
            if not any(str(s).startswith("note_") for s in sources):
                failures.append(
                    f"selected note not in context sources: {sources}"
                )

        # New note write
        events.clear()
        bus.publish(
            "ui.command",
            {"text": "new note: Quick capture from gate test"},
            source="test",
        )
        if not _wait_for(events, "note.created"):
            failures.append("new note: did not create note")
        else:
            created = payloads.get("note.created", {}).get("path", "")
            full = vault / created if created else None
            if full is None or not full.is_file():
                failures.append("created note file missing on disk")

        for svc in (handler, ollama, obsidian, router):
            svc.unload()
        db.close()

    handler_src = (
        PROJECT_ROOT / "ai_command_center" / "services" / "chat_handler_service.py"
    ).read_text(encoding="utf-8")
    if "get_context_notes" not in handler_src:
        failures.append("chat_handler must use ObsidianService.get_context_notes()")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 3C — Obsidian FTS, write, note injection")
    print("  note:roadmap -> search -> select -> chat sources include note_*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
