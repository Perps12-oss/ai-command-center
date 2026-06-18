#!/usr/bin/env python3
"""Phase 3D gate — session persistence, history in context, clipboard routing."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _wait(events: list[str], topic: str, timeout: float = 5.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if topic in events:
            return True
        time.sleep(0.02)
    return False


def main() -> int:
    print("=== Phase 3D Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.application import create_application

    app = create_application(debug_mode=True)
    for name in ("session", "chat_handler"):
        if app.services.get(name) is None:
            failures.append(f"service not registered: {name}")
    app.shutdown()

    from ai_command_center.core.context_manager import ContextBundle, ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.db.connection import connect, init_database
    from ai_command_center.db.conversation_repository import ConversationRepository
    from ai_command_center.services.chat_handler_service import ChatHandlerService
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.ollama_service import StubOllamaService
    from ai_command_center.services.session_service import SessionService

    class RecordingStub(StubOllamaService):
        last_bundle: ContextBundle | None = None

        def stream_chat(self, bundle, *, model, request_id=None):
            RecordingStub.last_bundle = bundle
            return super().stream_chat(bundle, model=model, request_id=request_id)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "phase3d.db"
        db = connect(db_path)
        init_database(db)
        try:
            bus = EventBus(debug_mode=True)
            events: list[str] = []
            payloads: dict[str, dict] = {}

            def tap(event) -> None:
                events.append(event.topic)
                payloads[event.topic] = dict(event.payload)

            bus.subscribe_all(tap)

            conv = ConversationRepository(db)
            session = SessionService(bus, conv)
            router = CommandRouterService(bus)
            ollama = RecordingStub(bus)
            handler = ChatHandlerService(
                bus, ContextManager(), ollama, session=session
            )
            for svc in (session, router, ollama, handler):
                svc.load()

            bus.publish(
                "settings.snapshot",
                {"default_model": "llama3.2:3b"},
                source="test",
            )

            if not _wait(events, "chat.history_loaded"):
                failures.append("session did not publish chat.history_loaded")
            elif payloads.get("chat.history_loaded", {}).get("messages"):
                failures.append("fresh session should start with empty history")

            # First turn
            events.clear()
            bus.publish("ui.command", {"text": "Hello session"}, source="test")
            if not _wait(events, "chat.complete"):
                failures.append("first chat did not complete")

            if conv.message_count() != 2:
                failures.append(
                    f"expected 2 messages after turn 1, got {conv.message_count()}"
                )

            # Simulate restart — reload session from same db
            for svc in (handler, ollama, router, session):
                svc.unload()

            bus2 = EventBus(debug_mode=True)
            events2: list[str] = []
            payloads2: dict[str, dict] = {}

            def tap2(event) -> None:
                events2.append(event.topic)
                payloads2[event.topic] = dict(event.payload)

            bus2.subscribe_all(tap2)

            conv2 = ConversationRepository(db)
            session2 = SessionService(bus2, conv2)
            router2 = CommandRouterService(bus2)
            ollama2 = RecordingStub(bus2)
            handler2 = ChatHandlerService(
                bus2, ContextManager(), ollama2, session=session2
            )
            for svc in (session2, router2, ollama2, handler2):
                svc.load()
            bus2.publish("settings.snapshot", {"default_model": "test"}, source="test")

            if not _wait(events2, "chat.history_loaded"):
                failures.append("reload did not publish history")
            else:
                msgs = payloads2.get("chat.history_loaded", {}).get("messages", [])
                if len(msgs) != 2:
                    failures.append(f"reload expected 2 messages, got {len(msgs)}")

            events2.clear()
            RecordingStub.last_bundle = None
            bus2.publish("ui.command", {"text": "Follow-up question"}, source="test")
            if not _wait(events2, "chat.complete"):
                failures.append("second chat did not complete")

            bundle = RecordingStub.last_bundle
            if bundle is None:
                failures.append("no ContextBundle on follow-up")
            elif "conversation_history" not in bundle.sources:
                failures.append(
                    f"history not in context sources: {bundle.sources}"
                )
            elif "Hello session" not in bundle.prompt:
                failures.append("prior user message missing from prompt")

            for svc in (handler2, ollama2, router2, session2):
                svc.unload()
        finally:
            db.close()

    # Clipboard forwarded to chat args
    router_src = (
        PROJECT_ROOT / "ai_command_center" / "services" / "command_router_service.py"
    ).read_text(encoding="utf-8")
    if "clipboard" not in router_src:
        failures.append("CommandRouter must forward clipboard for chat")

    handler_src = (
        PROJECT_ROOT / "ai_command_center" / "services" / "chat_handler_service.py"
    ).read_text(encoding="utf-8")
    if "conversation_history" not in handler_src:
        failures.append("ChatHandler must pass conversation_history")

    from ai_command_center.ui.ui_queue import UIQueue
    import inspect

    if "SimpleQueue" not in inspect.getsource(UIQueue):
        failures.append("UIQueue must use thread-safe SimpleQueue")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 3D — persistence, history context, clipboard path")
    print("  restart -> 2 messages restored -> follow-up includes conversation_history")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
