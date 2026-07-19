#!/usr/bin/env python3
"""Phase 1 gate: Services → Events → AppState (bus-only mutations, no repo shortcuts)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_command_center.application import create_application  # noqa: E402
from ai_command_center.core.event_bus import WildcardSubscriptionError  # noqa: E402
from ai_command_center.ui.design_system import theme_v2 as T  # noqa: E402


def main() -> int:
    print("=== Phase 1 Gate Verification ===")
    failures: list[str] = []
    received_topics: list[str] = []

    def tap(event) -> None:
        received_topics.append(event.topic)

    app = create_application(debug_mode=True)
    app.bus.subscribe("settings.changed", tap)
    app.bus.subscribe("settings.snapshot", tap)
    app.bus.subscribe("service.state_changed", tap)

    try:
        app.startup()
        snapshot = app.state_store.snapshot

        if snapshot.settings.default_model != "llama3.2:3b":
            failures.append(
                f"AppState.settings.default_model expected llama3.2:3b, "
                f"got {snapshot.settings.default_model!r}"
            )
        valid_themes = {"dark", "light"} | set(T.THEMES.keys())
        if snapshot.settings.theme not in valid_themes:
            failures.append(
                f"AppState.settings.theme not projected: {snapshot.settings.theme!r}"
            )

        app.bus.publish(
            "settings.set_request",
            {"key": "hotkey", "value": "alt+space"},
            source="verify_phase1",
        )
        after = app.state_store.snapshot
        if after.settings_version < 1:
            failures.append("settings.changed did not bump settings_version")
        if after.settings.hotkey != "alt+space":
            failures.append("settings.snapshot did not update hotkey in AppState")

        if "service.state_changed" not in received_topics:
            failures.append("no service.state_changed events received")
        if "settings.snapshot" not in received_topics:
            failures.append("no settings.snapshot events received")

        if not any(s.name == "settings" for s in snapshot.services):
            failures.append("AppState missing settings service snapshot")

        if hasattr(app, "settings_repo"):
            failures.append("ApplicationCore must not expose settings_repo")

        prod_bus = __import__(
            "ai_command_center.core.event_bus", fromlist=["EventBus"]
        ).EventBus(debug_mode=False)
        try:
            prod_bus.subscribe_all(lambda e: None)
            failures.append("subscribe_all should raise without debug_mode")
        except WildcardSubscriptionError:
            pass

        app.bus.subscribe("execution.authority.decision", tap)
        app.bus.publish(
            "ui.command",
            {"text": "hello phase 3"},
            source="verify_phase1",
        )
        decided = app.state_store.snapshot
        if decided.last_command_intent != "llm":
            failures.append(
                "execution.authority.decision expected llm capability, "
                f"got {decided.last_command_intent!r}"
            )

        app.shutdown()
        if app.services.any_loaded():
            failures.append("services still loaded after shutdown")

        if failures:
            print("FAIL:")
            for item in failures:
                print(f"  - {item}")
            return 1

        print("PASS: event bus, app state, settings.snapshot, execution authority, service manager")
        print(f"  events seen: {sorted(set(received_topics))}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        try:
            app.shutdown()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
