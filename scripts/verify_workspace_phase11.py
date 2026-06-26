#!/usr/bin/env python3
"""Workspace OS Phase 11 gate — workspace context in the chat pipeline + HomeView panel.

Verifies the resolved workspace (and its pre-AI suggestions) flow into the canonical
chat pipeline and surface in a dedicated HomeView panel:

  * ContextManager.build_context(workspace=...) emits a ``[workspace]`` framing block.
  * For a single ui.command the workspace is resolved *before* command.routed fires,
    so ChatHandlerService frames the ContextBundle with the active workspace
    (``workspace`` appears in chat.started sources).
  * HomeView exposes update_workspace(...) and app.py drives it from workspace.resolved
    (without importing the workspace service — architecture boundary preserved).
"""

from __future__ import annotations

import sys
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
    print("=== Workspace OS Phase 11 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.services.chat_handler_service import ChatHandlerService
    from ai_command_center.services.command_router_service import CommandRouterService
    from ai_command_center.services.ollama_service import StubOllamaService
    from ai_command_center.services.workspace_service import WorkspaceService

    # 1. ContextManager turns a workspace framing into a dedicated block + source.
    bundle = ContextManager().build_context("hello", workspace="Active workspace: Repo X")
    if "workspace" not in bundle.sources:
        failures.append("build_context(workspace=...) should add a 'workspace' source")
    if "[workspace]" not in bundle.prompt:
        failures.append("build_context should emit a [workspace] block in the prompt")
    if "Repo X" not in bundle.prompt:
        failures.append("workspace framing text should appear in the prompt")

    # Blank/whitespace workspace framing is ignored (no empty section).
    blank = ContextManager().build_context("hello", workspace="   ")
    if "workspace" in blank.sources:
        failures.append("whitespace-only workspace should not create a section")

    # 2. End-to-end ordering: workspace resolves before command.routed, so the chat
    #    pipeline frames the bundle with the active workspace.
    bus = EventBus(debug_mode=True)
    cm = ContextManager()
    ollama = StubOllamaService(bus)
    workspace = WorkspaceService(bus)
    router = CommandRouterService(bus)
    chat = ChatHandlerService(bus, cm, ollama)

    # Load order mirrors the composition root: workspace before the command router.
    ollama.load()
    workspace.load()
    router.load()
    chat.load()

    events: list[str] = []
    payloads: dict[str, dict] = {}

    def tap(event) -> None:
        events.append(event.topic)
        payloads[event.topic] = dict(event.payload)

    bus.subscribe_all(tap)

    bus.publish("ui.command", {"text": "explain this code"}, source="ui")

    if not _wait(events, "chat.started"):
        failures.append("chat.started not published — chat pipeline did not run")
    else:
        sources = payloads["chat.started"].get("sources", [])
        if "workspace" not in sources:
            failures.append(
                "workspace context missing from chat bundle sources "
                f"(got {sources!r})"
            )

    chat.unload()
    router.unload()
    workspace.unload()

    # 3. Composition root resolves the workspace before routing the command.
    app_src = (PROJECT_ROOT / "ai_command_center" / "application.py").read_text(encoding="utf-8")
    if "WorkspaceService(bus)" in app_src and "CommandRouterService(bus)" in app_src:
        if app_src.index("WorkspaceService(bus)") > app_src.index("CommandRouterService(bus)"):
            failures.append(
                "WorkspaceService must be registered before CommandRouterService "
                "so workspace.resolved precedes command.routed"
            )

    # 4. ChatHandlerService subscribes to workspace.resolved to cache the framing.
    chat_src = (
        PROJECT_ROOT / "ai_command_center" / "services" / "chat_handler_service.py"
    ).read_text(encoding="utf-8")
    if "workspace.resolved" not in chat_src:
        failures.append("ChatHandlerService should subscribe to workspace.resolved")

    # 5. HomeView surfaces a dedicated workspace panel, driven from the bus by app.py,
    #    without the UI importing the workspace service (architecture boundary).
    home_src = (
        PROJECT_ROOT / "ai_command_center" / "ui" / "views" / "home_view.py"
    ).read_text(encoding="utf-8")
    if "def update_workspace" not in home_src:
        failures.append("HomeView must expose update_workspace(...) for the panel")
    if "ACTIVE WORKSPACE" not in home_src:
        failures.append("HomeView should render a dedicated ACTIVE WORKSPACE section")

    app_ui_src = (
        PROJECT_ROOT / "ai_command_center" / "ui" / "app.py"
    ).read_text(encoding="utf-8")
    if "update_workspace(" not in app_ui_src:
        failures.append("app.py should drive HomeView.update_workspace from the bus")
    if "WorkspaceService" in app_ui_src or "workspace_service" in app_ui_src:
        failures.append("UI must not import WorkspaceService directly")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 11 — workspace context in chat pipeline + HomeView panel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
