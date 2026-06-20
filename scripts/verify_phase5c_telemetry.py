#!/usr/bin/env python3
"""Phase 5C+ gate — passive telemetry layer (observation only)."""

from __future__ import annotations

import inspect
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_FORBIDDEN_RUNTIME_TOKENS = (
    "_PendingCommand",
    "_PaletteSession",
    "ui.hesitation",
    "command.retry",
    "command.invoked",
    "command.executed",
    "eventbus.dispatch_time",
)


def main() -> int:
    print("=== Phase 5C+ Telemetry Gate ===")
    failures: list[str] = []

    tel_src = (PROJECT_ROOT / "ai_command_center" / "services" / "telemetry_service.py").read_text(
        encoding="utf-8"
    )
    if "subscribe_all" in tel_src:
        failures.append("TelemetryService must not use subscribe_all")
    if "self._bus.publish" in tel_src:
        failures.append("TelemetryService must not publish to EventBus")
    for token in _FORBIDDEN_RUNTIME_TOKENS:
        if token in tel_src:
            failures.append(f"runtime inference forbidden in TelemetryService: {token}")

    ui_files = list((PROJECT_ROOT / "ai_command_center" / "ui").rglob("*.py"))
    ui_src = "\n".join(p.read_text(encoding="utf-8") for p in ui_files)
    if "telemetry" in ui_src.lower():
        failures.append("UI must not import telemetry modules")

    from ai_command_center.application import create_application
    from ai_command_center.db.telemetry_repository import TelemetryRepository
    from ai_command_center.services.telemetry_summary import compute_session_summary

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "telemetry_gate.db"
        from ai_command_center.db.connection import connect, init_database

        db = connect(db_path)
        init_database(db)

        from ai_command_center.core.event_bus import EventBus
        from ai_command_center.db.repository import SettingsRepository
        from ai_command_center.services.command_router_service import CommandRouterService
        from ai_command_center.services.telemetry_service import TelemetryService
        from ai_command_center.services.settings_service import SettingsService

        bus = EventBus(debug_mode=True)
        repo = TelemetryRepository(db)
        telemetry = TelemetryService(bus, repo)
        settings = SettingsService(bus, SettingsRepository(db))
        router = CommandRouterService(bus)
        for svc in (telemetry, settings, router):
            svc.load()

        app = create_application(debug_mode=True)
        if app.services.get("telemetry") is None:
            failures.append("telemetry not registered in application")
        app.shutdown()

        bus2 = EventBus(debug_mode=True)
        repo2 = TelemetryRepository(db)
        tel2 = TelemetryService(bus2, repo2)
        tel2.load()
        session_id = tel2.session_id

        bus2.publish("ui.palette_open", {}, source="ui")
        bus2.publish("ui.command", {"text": "hello"}, source="ui")
        bus2.publish(
            "command.routed",
            {
                "intent": "chat",
                "status": "pending",
                "text": "hello",
                "args": {"prompt": "hello"},
            },
            source="command_router",
        )
        bus2.publish(
            "context.snapshot_created",
            {"context_size_tokens": 42, "sources": ["user_query"], "budget_tokens": 2800},
            source="chat_handler",
        )
        bus2.publish("chat.started", {"request_id": "r1"}, source="ollama")
        time.sleep(0.01)
        bus2.publish("chat.complete", {"request_id": "r1", "text": "hi"}, source="ollama")
        bus2.publish("ui.palette_close", {}, source="ui")

        if repo2.count() < 5:
            failures.append(f"expected >=5 telemetry rows, got {repo2.count()}")

        rows = repo2.fetch_session(session_id)
        events = {r["event"] for r in rows}
        for required in (
            "ui.command",
            "chat.complete",
            "context.snapshot_created",
            "ui.palette_open",
        ):
            if required not in events:
                failures.append(f"missing raw telemetry event: {required}")

        summary = compute_session_summary(rows)
        if summary["commands"]["success"] < 1:
            failures.append("offline summary did not derive command success")

        tel2.unload()
        db.close()

    from ai_command_center.services.telemetry_service import TelemetryService as TS

    src = inspect.getsource(TS)
    for token in ("stream_chat", "build_context", "resolve(", "AppStateStore"):
        if token in src:
            failures.append(f"TelemetryService must not reference {token}")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 5C+ telemetry — dumb runtime, offline derived summary")
    print(f"  summary friction: {summary.get('friction_score')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
