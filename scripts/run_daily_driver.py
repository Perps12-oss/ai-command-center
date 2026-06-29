#!/usr/bin/env python3
"""
Daily-driver automation — headless Tests A & C against live Ollama.

UI steps (Alt+Space, friction/usability scores) remain manual; see docs/ARCHITECTURE.md#gate-history.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_CLIPBOARD_SAMPLE = (
    "Q3 product roadmap priorities:\n"
    "1. Cut mobile app cold-start time below 2 seconds.\n"
    "2. Ship stable public API v2 with migration guides.\n"
    "3. Reduce new-user onboarding from six steps to three.\n"
    "4. Improve offline sync reliability for field teams.\n"
)

_MODEL = "llama3.2:3b"
_LATENCY_GOAL_S = 10.0


def _wait(events: list[str], topic: str, timeout: float) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if topic in events:
            return True
        time.sleep(0.02)
    return False


def _wire_stack(db_path: Path):
    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.db.conversation_repository import ConversationRepository
    from ai_command_center.db.note_repository import NoteRepository
    from ai_command_center.db.repository import SettingsRepository
    from ai_command_center.services.chat_handler_service import ChatHandlerService
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.obsidian_service import ObsidianService
    from ai_command_center.services.ollama_http_service import OllamaHttpService
    from ai_command_center.services.session_service import SessionService
    from ai_command_center.services.settings_service import SettingsService

    db = connect(db_path)
    init_database(db)
    bus = EventBus(debug_mode=True)
    events: list[str] = []
    payloads: dict[str, dict] = {}

    def tap(event) -> None:
        events.append(event.topic)
        payloads[event.topic] = dict(event.payload)

    bus.subscribe_all(tap)

    settings = SettingsService(bus, SettingsRepository(db))
    router = CommandRouterService(bus)
    ollama = OllamaHttpService(bus)
    obsidian = ObsidianService(bus, NoteRepository(db))
    session = SessionService(bus, ConversationRepository(db))
    handler = ChatHandlerService(bus, ContextManager(), ollama, obsidian, session)
    services = (settings, router, ollama, obsidian, session, handler)
    for svc in services:
        svc.load()

    return bus, services, events, payloads, db


def _unload(services, db) -> None:
    for svc in reversed(services):
        svc.unload()
    db.close()


def test_a_clipboard_summarize(db_path: Path) -> dict:
    bus, services, events, payloads, db = _wire_stack(db_path)
    try:
        if not _wait(events, "settings.snapshot", 3.0):
            return {"pass": False, "error": "settings.snapshot timeout"}

        events.clear()
        t0 = time.perf_counter()
        bus.publish(
            "ui.command",
            {
                "text": "Summarize this clipboard",
                "clipboard": _CLIPBOARD_SAMPLE,
            },
            source="daily_driver",
        )
        if not _wait(events, "chat.started", 5.0):
            return {"pass": False, "error": "chat.started timeout"}
        if not _wait(events, "chat.complete", 90.0):
            err = payloads.get("chat.error", {})
            return {
                "pass": False,
                "error": f"chat.complete timeout: {err.get('message', 'unknown')}",
            }
        latency_s = time.perf_counter() - t0
        complete = payloads.get("chat.complete", {})
        response = str(complete.get("text", "")).strip()
        if len(response) < 20:
            return {"pass": False, "error": f"response too short: {response!r}"}

        sources = payloads.get("chat.started", {}).get("sources", [])
        if "clipboard" not in sources:
            return {"pass": False, "error": f"clipboard not in sources: {sources}"}

        # Simulate close + reopen
        _unload(services, db)
        bus2, services2, events2, payloads2, db2 = _wire_stack(db_path)
        try:
            if not _wait(events2, "chat.history_loaded", 3.0):
                return {"pass": False, "error": "chat.history_loaded on reopen timeout"}
            history = payloads2.get("chat.history_loaded", {}).get("messages", [])
            if len(history) < 2:
                return {
                    "pass": False,
                    "error": f"expected >=2 messages after reopen, got {len(history)}",
                }
            roles = [m.get("role") for m in history]
            if "user" not in roles or "assistant" not in roles:
                return {"pass": False, "error": f"unexpected history roles: {roles}"}
        finally:
            _unload(services2, db2)

        return {
            "pass": True,
            "latency_s": round(latency_s, 2),
            "under_10s": latency_s < _LATENCY_GOAL_S,
            "response_chars": len(response),
            "sources": list(sources),
        }
    finally:
        if db:
            try:
                _unload(services, db)
            except Exception:
                db.close()


def test_c_failure_recovery(db_path: Path) -> dict:
    bus, services, events, payloads, db = _wire_stack(db_path)
    try:
        _wait(events, "settings.snapshot", 3.0)
        events.clear()
        bus.publish(
            "settings.set_request",
            {"key": "ollama_url", "value": "http://127.0.0.1:1"},
            source="daily_driver",
        )
        _wait(events, "settings.snapshot", 2.0)
        events.clear()
        bus.publish(
            "ui.command",
            {"text": "Say hello briefly"},
            source="daily_driver",
        )
        if not _wait(events, "chat.error", 10.0):
            return {"pass": False, "error": "expected chat.error when Ollama offline"}
        offline_msg = str(payloads.get("chat.error", {}).get("message", ""))

        events.clear()
        bus.publish(
            "settings.set_request",
            {"key": "ollama_url", "value": "http://127.0.0.1:11434"},
            source="daily_driver",
        )
        _wait(events, "settings.snapshot", 2.0)
        events.clear()
        bus.publish(
            "ui.command",
            {"text": "Reply with exactly: recovered"},
            source="daily_driver",
        )
        if not _wait(events, "chat.complete", 90.0):
            return {"pass": False, "error": "retry after restore did not complete"}
        text = str(payloads.get("chat.complete", {}).get("text", "")).strip()
        if not text:
            return {"pass": False, "error": "retry returned empty response"}

        return {"pass": True, "offline_message": offline_msg[:120], "retry_chars": len(text)}
    finally:
        _unload(services, db)


def main() -> int:
    print("=== Daily Driver (automated) ===\n")
    failures: list[str] = []
    report: dict[str, object] = {"date": date.today().isoformat(), "tests": {}}

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "daily_driver.db"

        print("--- Test A: Clipboard summarize + history persist ---")
        test_a = test_a_clipboard_summarize(db_path)
        report["tests"]["A_clipboard"] = test_a
        print(json.dumps(test_a, indent=2))
        if not test_a.get("pass"):
            failures.append(f"Test A: {test_a.get('error', 'failed')}")
        else:
            lat = test_a.get("latency_s")
            goal = "OK" if test_a.get("under_10s") else "SLOW"
            print(f"  Latency: {lat}s ({goal}, goal <{_LATENCY_GOAL_S}s)")

        print("\n--- Test C: Failure recovery ---")
        test_c = test_c_failure_recovery(db_path)
        report["tests"]["C_recovery"] = test_c
        print(json.dumps(test_c, indent=2))
        if not test_c.get("pass"):
            failures.append(f"Test C: {test_c.get('error', 'failed')}")

    print("\n--- Manual UI (not automated) ---")
    print("  Test A steps 2,5,6: Alt+Space palette open/close — verify visually")
    print("  Test B (notes): optional — requires obsidian_vault_path")
    print("  Friction / Usability / Predictability: score 1-5 in PHASE_LEDGER")

    if failures:
        report["verdict"] = "PARTIAL" if test_a.get("pass") or test_c.get("pass") else "FAIL"
        print("\nFAIL:")
        for item in failures:
            print(f"  - {item}")
        print(json.dumps(report, indent=2))
        return 1

    verdict = "PASS"
    if not test_a.get("pass") or not test_c.get("pass"):
        verdict = "PARTIAL" if test_a.get("pass") or test_c.get("pass") else "FAIL"
    elif not test_a.get("under_10s"):
        verdict = "PARTIAL"
    report["verdict"] = verdict
    print(f"\nAutomated daily-driver: {verdict}")
    if test_a.get("pass") and not test_a.get("under_10s"):
        print(f"  Note: latency {test_a.get('latency_s')}s exceeded {_LATENCY_GOAL_S}s goal")
    print(json.dumps(report, indent=2))
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
