#!/usr/bin/env python3
"""Phase 2 structural gate — UI shell, architecture compliance, no headless GUI required."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = PROJECT_ROOT / "ai_command_center" / "ui"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _grep_ui_for_forbidden_imports() -> list[str]:
    failures: list[str] = []
    forbidden = ("db.repository", "services.settings_service", "ServiceManager")
    for path in UI_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                failures.append(f"{path.name} references forbidden {token}")
    return failures


def main() -> int:
    print("=== Phase 2 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.ui.ui_queue import UI_STREAM_INTERVAL_MS

    if UI_STREAM_INTERVAL_MS != 50:
        failures.append(f"UI_STREAM_INTERVAL_MS expected 50, got {UI_STREAM_INTERVAL_MS}")

    from ai_command_center.ui.design_system import theme_v2 as T

    if T.WINDOW_WIDTH != 1100 or T.WINDOW_HEIGHT != 700:
        failures.append("Window size not 1100x700")
    if T.FADE_IN_MS != 150:
        failures.append("Fade duration not 150ms")

    from ai_command_center.ui.controller import UIController

    src = inspect.getsource(UIController)
    if "ApplicationCore" in src:
        failures.append("UIController must not reference ApplicationCore")
    if "repository" in src.lower() or "ServiceManager" in src:
        failures.append("UIController must not reference repositories or ServiceManager")

    app_src = (UI_ROOT / "app.py").read_text(encoding="utf-8")
    if "ApplicationCore" in app_src:
        failures.append("ui/app.py must not import ApplicationCore")
    if "_core" in app_src:
        failures.append("ui/app.py must not hold _core reference")

    failures.extend(_grep_ui_for_forbidden_imports())

    from ai_command_center.core.event_bus import EventBus, WildcardSubscriptionError

    bus = EventBus(debug_mode=False)
    try:
        bus.subscribe_all(lambda e: None)
        failures.append("production bus should block subscribe_all")
    except WildcardSubscriptionError:
        pass

    # Import smoke test (does not open GUI)
    from ai_command_center.ui.app import CommandPaletteApp  # noqa: F401

    from ai_command_center.utils.hotkey import validate_hotkey

    hk_ok, _ = validate_hotkey()
    if not hk_ok:
        failures.append("keyboard library not available for hotkey")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 2 UI shell, tokens, UIQueue, architecture guards")
    print("  Manual: run main.py, Alt+Space toggles palette, tray icon works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
