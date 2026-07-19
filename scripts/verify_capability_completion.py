#!/usr/bin/env python3
"""Capability completion gate — clipboard, routing, vault UX fixes."""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _wait(events: list[str], topic: str, timeout: float = 3.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if topic in events:
            return True
        time.sleep(0.02)
    return False


def main() -> int:
    print("=== Capability Completion Gate ===")
    failures: list[str] = []

    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.core.events.topics import LLM_STEP_REQUEST
    from ai_command_center.services.command_router_service import (
        CommandRouterService,
        INTENT_NAVIGATE,
        INTENT_SHELL,
    )

    cases = (
        ("settings", INTENT_NAVIGATE, "settings"),
        ("echo phase5c-test", INTENT_SHELL, "echo phase5c-test"),
        ("> echo ok", INTENT_SHELL, "echo ok"),
        ("go chat", INTENT_NAVIGATE, "chat"),
    )
    for text, expected_intent, expected_arg_fragment in cases:
        got_intent, args = CommandRouterService.classify(text)
        if got_intent != expected_intent:
            failures.append(f"{text!r}: intent {got_intent} != {expected_intent}")
        blob = str(args).lower()
        if expected_arg_fragment.lower() not in blob:
            failures.append(f"{text!r}: args missing {expected_arg_fragment!r} ({args})")

    # Clipboard guard in chat handler through the llm capability path.
    import tempfile
    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.repositories.conversation_repository import ConversationRepository
    from ai_command_center.repositories.settings_repository import SettingsRepository
    from ai_command_center.services.chat_handler_service import ChatHandlerService
    from ai_command_center.services.ollama_http_service import OllamaHttpService
    from ai_command_center.services.session_service import SessionService
    from ai_command_center.services.settings_service import SettingsService

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = connect(Path(tmp) / "cap.db")
        init_database(db)
        bus2 = EventBus(debug_mode=True)
        errors: list[dict] = []
        bus2.subscribe("chat.error", lambda e: errors.append(dict(e.payload)))
        settings = SettingsService(bus2, SettingsRepository(db))
        session = SessionService(bus2, ConversationRepository(db))
        ollama = OllamaHttpService(bus2)
        handler = ChatHandlerService(bus2, ContextManager(), session=session)
        for svc in (settings, session, ollama, handler):
            svc.load()
        bus2.publish(
            LLM_STEP_REQUEST,
            {
                "request_id": "clip-empty",
                "run_id": "run-clip",
                "step_id": "step-1",
                "capability": "llm",
                "args": {"prompt": "Summarize this clipboard", "clipboard": ""},
                "prompt": "Summarize this clipboard",
            },
            source="execution_orchestrator",
        )
        time.sleep(0.1)
        if not errors:
            failures.append("empty clipboard should emit chat.error")
        elif "empty" not in str(errors[0].get("message", "")).lower():
            failures.append(f"unexpected clipboard error: {errors[0]}")
        for svc in (handler, ollama, session, settings):
            svc.unload()
        db.close()
        db = None
        import gc

        gc.collect()
        time.sleep(0.2)

    settings_py = (PROJECT_ROOT / "ai_command_center" / "ui" / "views" / "settings_view.py").read_text(
        encoding="utf-8"
    )
    if "_vault_banner" not in settings_py:
        failures.append("settings_view missing vault banner")
    if "is_dir()" not in settings_py:
        failures.append("settings_view missing vault path validation")

    help_py = PROJECT_ROOT / "ai_command_center" / "ui" / "capability_help.py"
    if not help_py.is_file():
        failures.append("capability_help.py missing")

    event_coordinator_py = (
        PROJECT_ROOT / "ai_command_center" / "ui" / "shell" / "event_coordinator.py"
    ).read_text(encoding="utf-8")
    if "_on_ui_navigate" not in event_coordinator_py:
        failures.append("shell event coordinator missing UI_NAVIGATE handler")

    ollama_py = (
        PROJECT_ROOT / "ai_command_center" / "services" / "ollama_http_service.py"
    ).read_text(encoding="utf-8")
    if '"role": "system"' not in ollama_py:
        failures.append("ollama missing local assistant system prompt")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: capability_completion — clipboard guard, routing, vault UX, help")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
