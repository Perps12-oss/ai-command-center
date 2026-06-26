#!/usr/bin/env python3
"""Workspace OS Phase 10 gate — runtime/service wiring (EventBus + AppState + UI).

Verifies the pure v3.5 workspace domain is integrated into the running system:
WorkspaceService resolves on ``ui.command`` and publishes ``workspace.resolved``,
AppState projects it into a ``WorkspaceSnapshot``, and the UI consumes it via the bus
(no direct service/repository imports).
"""

from __future__ import annotations

import os
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
    print("=== Workspace OS Phase 10 Gate Verification ===")
    failures: list[str] = []

    runtime_dir = tempfile.mkdtemp(prefix="ws_phase10_")
    os.environ.setdefault("APPDATA", runtime_dir)
    os.environ.setdefault("XDG_DATA_HOME", runtime_dir)

    from ai_command_center.application import create_application
    from ai_command_center.core.app_state import AppStateStore, WorkspaceSnapshot
    from ai_command_center.core.contracts import WORKSPACE_RESOLVED_VERSION
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.services.workspace_service import WorkspaceService

    # 1. WorkspaceService is registered in the composition root.
    app = create_application(debug_mode=True)
    if app.services.get("workspace") is None:
        failures.append("workspace service not registered in application")
    app.shutdown()

    # 2. ui.command -> workspace.resolved with the locked contract version.
    bus = EventBus(debug_mode=True)
    state_store = AppStateStore(bus)
    events: list[str] = []
    payloads: dict[str, dict] = {}

    def tap(event) -> None:
        events.append(event.topic)
        payloads[event.topic] = dict(event.payload)

    bus.subscribe_all(tap)

    service = WorkspaceService(bus)
    service.load()

    bus.publish(
        "settings.snapshot",
        {"obsidian_vault_path": "/home/user/vault"},
        source="test",
    )
    bus.publish("ui.command", {"text": "summarize my notes"}, source="ui")

    if not _wait(events, "workspace.resolved"):
        failures.append("workspace.resolved not published after ui.command")
    else:
        wp = payloads["workspace.resolved"]
        if wp.get("contract_version") != WORKSPACE_RESOLVED_VERSION:
            failures.append("workspace.resolved missing/incorrect contract_version")
        if not str(wp.get("workspace_id", "")).startswith("ws-"):
            failures.append("workspace.resolved missing deterministic workspace_id")
        if wp.get("evidence_source") != "obsidian_vault":
            failures.append("vault path should drive evidence_source=obsidian_vault")

    # 3. AppState projects workspace.resolved into a WorkspaceSnapshot.
    snap = state_store.snapshot
    if not isinstance(snap.workspace, WorkspaceSnapshot):
        failures.append("AppState.workspace should be a WorkspaceSnapshot")
    elif not snap.workspace.workspace_id:
        failures.append("AppState.workspace not populated from workspace.resolved")

    # 4. Determinism: identical evidence -> identical workspace_id (A5).
    first_id = payloads["workspace.resolved"].get("workspace_id")
    events.clear()
    bus.publish("ui.command", {"text": "another command"}, source="ui")
    _wait(events, "workspace.resolved")
    if payloads["workspace.resolved"].get("workspace_id") != first_id:
        failures.append("workspace_id should stay stable for same vault evidence")

    # 5. Pre-AI suggestions surface for a clipboard traceback.
    events.clear()
    traceback_text = "Traceback (most recent call last):\n  File x\nValueError: boom"
    bus.publish(
        "ui.command",
        {"text": "what is this", "clipboard": traceback_text},
        source="ui",
    )
    _wait(events, "workspace.resolved")
    labels = [s.get("label") for s in payloads["workspace.resolved"].get("suggestions", [])]
    if "Explain Error" not in labels:
        failures.append("clipboard traceback should yield pre-AI suggestions")

    service.unload()
    state_store.close()

    # 6. UI layer consumes via the bus and does not import the workspace service
    #    or repositories directly (architecture boundary).
    ui_files = list((PROJECT_ROOT / "ai_command_center" / "ui").rglob("*.py"))
    ui_src = "\n".join(p.read_text(encoding="utf-8") for p in ui_files)
    if "workspace_service" in ui_src or "WorkspaceService" in ui_src:
        failures.append("UI must not import WorkspaceService directly")
    if "workspace.resolved" not in ui_src:
        failures.append("UI should subscribe to workspace.resolved via the bus")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 10 — runtime/service wiring (EventBus + AppState + UI)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
