#!/usr/bin/env python3
"""Knowledge Access Verification Gate — capability outcomes only (headless EventBus)."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_CLIP = "ROADMAP LINE: cut cold-start below 2 seconds."
_HISTORY = [("user", "unrelated old question"), ("assistant", "unrelated old answer")] * 6


def _wait(events: list[str], topic: str, timeout: float = 12.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if topic in events:
            return True
        time.sleep(0.02)
    return False


def _wire(
    db_path: Path,
    vault: Path,
    *,
    ollama_mode: str = "stub",
    ollama_url: str = "http://127.0.0.1:59999",
):
    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.repositories.conversation_repository import ConversationRepository
    from ai_command_center.repositories.note_repository import NoteRepository
    from ai_command_center.repositories.settings_repository import SettingsRepository
    from ai_command_center.services.chat_handler_service import ChatHandlerService
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.obsidian_service import ObsidianService
    from ai_command_center.services.ollama_http_service import OllamaHttpService
    from ai_command_center.services.ollama_service import StubOllamaService
    from ai_command_center.services.session_service import SessionService
    from ai_command_center.services.settings_service import SettingsService, _DEFAULTS

    db = connect(db_path)
    init_database(db)
    bus = EventBus(debug_mode=True)
    events: list[str] = []
    payloads: dict[str, list[dict]] = {}

    def tap(event) -> None:
        events.append(event.topic)
        payloads.setdefault(event.topic, []).append(dict(event.payload))

    bus.subscribe_all(tap)

    settings_repo = SettingsRepository(db)
    settings_repo.set("obsidian_vault_path", str(vault))
    if ollama_mode == "offline":
        settings_repo.set("ollama_url", ollama_url)

    settings = SettingsService(bus, settings_repo)
    router = CommandRouterService(bus)
    ollama = (
        OllamaHttpService(bus)
        if ollama_mode == "offline"
        else StubOllamaService(bus)
    )
    obsidian = ObsidianService(bus, NoteRepository(db), settings_repo)
    conv_repo = ConversationRepository(db)
    session = SessionService(bus, conv_repo)
    handler = ChatHandlerService(bus, ContextManager(), obsidian, session)
    services = (settings, router, ollama, obsidian, session, handler)
    for svc in services:
        svc.load()

    if ollama_mode == "offline":
        bus.publish(
            "settings.snapshot",
            {k: settings_repo.get(k, v) for k, v in _DEFAULTS.items()},
            source="gate",
        )
        time.sleep(0.2)

    if not _wait(events, "settings.snapshot", 5.0):
        raise RuntimeError("settings.snapshot timeout")

    return bus, services, events, payloads, db, session, conv_repo


def _unload(services, db) -> None:
    for svc in reversed(services):
        svc.unload()
    db.close()


def _last(payloads: dict[str, list[dict]], topic: str) -> dict:
    items = payloads.get(topic) or []
    return items[-1] if items else {}


def _seed_history(conv_repo) -> None:
    conv_repo.ensure_default(model="llama3.2:3b")
    for role, content in _HISTORY:
        conv_repo.append_message(role, content)


def main() -> int:
    results: dict[str, dict] = {}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "stress-test.md").write_text(
            "# Stress test\n\nThis is a test note for gate verification.\n",
            encoding="utf-8",
        )
        (vault / "clipboard-tips.md").write_text(
            "# Clipboard tips\nCopy text before summarize commands.\n",
            encoding="utf-8",
        )
        db_path = tmp_path / "gate.db"

        # --- 1. note: test returns results ---
        bus, services, events, payloads, db, _session, _conv = _wire(db_path, vault)
        try:
            events.clear()
            payloads.clear()
            bus.publish("ui.command", {"text": "note: test"}, source="gate")
            end = time.time() + 20.0
            hits: list[dict] = []
            while time.time() < end:
                for item in payloads.get("note.search_results", []):
                    if item.get("query") == "test" and item.get("results"):
                        hits = list(item["results"])
                        break
                if hits:
                    break
                time.sleep(0.02)
            paths = [str(h.get("path", "")) for h in hits]
            ok = "stress-test.md" in paths
            results["notes_search"] = {
                "pass": ok,
                "evidence": {
                    "query": "test",
                    "hit_count": len(hits),
                    "paths": paths,
                    "indexed_files": _last(payloads, "note.search_results").get(
                        "indexed_files"
                    ),
                },
            }
        finally:
            _unload(services, db)

        # --- 2. Use in chat injects selected note ---
        bus, services, events, payloads, db, _session, _conv = _wire(db_path, vault)
        try:
            events.clear()
            payloads.clear()
            bus.publish("ui.command", {"text": "note: test"}, source="gate")
            end = time.time() + 20.0
            while time.time() < end:
                sr = _last(payloads, "note.search_results")
                if sr.get("results"):
                    break
                time.sleep(0.02)

            bus.publish("note.select", {"path": "stress-test.md"}, source="gate")
            _wait(events, "note.selected", 5.0)
            selected = _last(payloads, "note.selected")

            events.clear()
            bus.publish("ui.command", {"text": "What does this note say?"}, source="gate")
            _wait(events, "chat.started", 8.0)
            sources = _last(payloads, "chat.started").get("sources", [])
            note_sources = [s for s in sources if str(s).startswith("note_")]
            ok = bool(selected.get("path")) and bool(note_sources)
            results["notes_injection"] = {
                "pass": ok,
                "evidence": {
                    "note.selected": selected,
                    "chat.started.sources": sources,
                    "note_sources": note_sources,
                },
            }
        finally:
            _unload(services, db)

        # --- 3. Clipboard intent variants ---
        clip_cases = (
            "Summarize this clipboard",
            "Summarize clipboad",
            "Summarize clip board",
            "Summarize this clip",
        )
        clip_evidence: dict[str, dict] = {}
        clip_ok = True
        for phrase in clip_cases:
            bus, services, events, payloads, db, session, conv = _wire(db_path, vault)
            try:
                events.clear()
                payloads.clear()
                bus.publish(
                    "ui.command",
                    {"text": phrase, "clipboard": _CLIP},
                    source="gate",
                )
                _wait(events, "context.snapshot_created", 5.0)
                snap = _last(payloads, "context.snapshot_created")
                sources = snap.get("sources", [])
                ok = "clipboard" in sources and "chat.error" not in events
                clip_evidence[phrase] = {
                    "pass": ok,
                    "sources": sources,
                    "chat.error": _last(payloads, "chat.error") or None,
                }
                if not ok:
                    clip_ok = False
            finally:
                _unload(services, db)
        results["clipboard_detection"] = {"pass": clip_ok, "evidence": clip_evidence}

        # --- 4. Empty clipboard visible error ---
        bus, services, events, payloads, db, _session, _conv = _wire(db_path, vault)
        try:
            events.clear()
            payloads.clear()
            for phrase in ("Summarize this clipboard", "Summarize clipboad"):
                bus.publish("ui.command", {"text": phrase, "clipboard": ""}, source="gate")
                time.sleep(0.15)
            errors = payloads.get("chat.error", [])
            messages = [str(e.get("message", "")) for e in errors]
            ok = len(errors) >= 2 and all("empty" in m.lower() for m in messages)
            results["empty_clipboard_handling"] = {
                "pass": ok,
                "evidence": {
                    "chat.error_count": len(errors),
                    "messages": messages,
                    "ui_path": "chat.error -> ChatView.show_error (EventBus)",
                },
            }
        finally:
            _unload(services, db)

        # --- 5. Ollama offline visible error ---
        bus, services, events, payloads, db, _session, conv = _wire(
            db_path, vault, ollama_mode="offline"
        )
        try:
            events.clear()
            payloads.clear()
            bus.publish(
                "ui.command",
                {"text": "hello offline test", "clipboard": _CLIP},
                source="gate",
            )
            end = time.time() + 12.0
            while time.time() < end:
                if "chat.error" in events:
                    break
                time.sleep(0.02)
            err = _last(payloads, "chat.error")
            msg = str(err.get("message", ""))
            ok = "ollama" in msg.lower() and "running" in msg.lower()
            results["ollama_error_surface"] = {
                "pass": ok,
                "evidence": {
                    "chat.error": err,
                    "ollama_url": "http://127.0.0.1:59999",
                    "ui_path": "chat.error -> ChatView.show_error (EventBus)",
                },
            }
        finally:
            _unload(services, db)

        # --- 6. Clipboard prioritized over history ---
        bus, services, events, payloads, db, session, conv = _wire(db_path, vault)
        try:
            _seed_history(conv)
            events.clear()
            payloads.clear()
            bus.publish(
                "ui.command",
                {"text": "Summarize this clipboard", "clipboard": _CLIP},
                source="gate",
            )
            _wait(events, "context.snapshot_created", 5.0)
            snap = _last(payloads, "context.snapshot_created")
            sources = snap.get("sources", [])
            ok = (
                "clipboard" in sources
                and "conversation_history" not in sources
                and "conversation_summary" not in sources
            )
            results["clipboard_priority"] = {
                "pass": ok,
                "evidence": {
                    "seeded_turns": len(_HISTORY),
                    "context.snapshot_created.sources": sources,
                    "history_excluded": "conversation_history" not in sources,
                },
            }
        finally:
            _unload(services, db)

    gate_pass = all(v["pass"] for v in results.values())
    results["knowledge_access_gate"] = {
        "pass": gate_pass,
        "evidence": {"checks": list(results.keys())},
    }

    print("knowledge_access_gate:")
    print(json.dumps(results["knowledge_access_gate"], indent=2))
    for key in (
        "notes_search",
        "notes_injection",
        "clipboard_detection",
        "clipboard_priority",
        "empty_clipboard_handling",
        "ollama_error_surface",
    ):
        print(f"{key}:")
        print(json.dumps(results[key], indent=2))
    print(f"verdict:\n{'PASS' if gate_pass else 'FAIL'}")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
