from __future__ import annotations

import time
from pathlib import Path

from ai_command_center.application import create_application
from ai_command_center.core.events import topics
from ai_command_center.db.connection import connect, init_database
from ai_command_center.ui.workspace_os_controller import WorkspaceOsUIController


def _wait_for(predicate, timeout_s: float = 6.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_first_command_auto_bootstraps_workspace_and_replays() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    deferred: list[dict] = []
    created: list[dict] = []
    tool_results: list[dict] = []

    unsubs = [
        core.bus.subscribe(topics.COMMAND_DEFERRED, lambda e: deferred.append(dict(e.payload))),
        core.bus.subscribe(topics.WORKSPACE_CREATED, lambda e: created.append(dict(e.payload))),
        core.bus.subscribe(topics.TOOL_RESULT, lambda e: tool_results.append(dict(e.payload))),
        core.bus.subscribe(
            topics.TOOL_CONFIRMATION_REQUIRED,
            lambda e: core.bus.publish(
                topics.TOOL_APPROVED,
                {"confirmation_id": str(e.payload.get("confirmation_id", ""))},
                source="test",
            ),
        ),
    ]

    try:
        core.startup()
        core.bus.publish(topics.UI_COMMAND, {"text": "> echo hello"}, source="test")
        assert _wait_for(lambda: bool(created), timeout_s=4.0)
        assert _wait_for(lambda: bool(tool_results), timeout_s=6.0)
        assert deferred, "expected initial command to defer before workspace bootstrap"
        assert tool_results[-1].get("tool") == "shell"
        assert tool_results[-1].get("success") is True
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()


def test_chat_fallback_stays_provider_relevant_when_llm_unavailable() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    controller = WorkspaceOsUIController(core.bus)
    chat_complete: list[dict] = []
    replan_requests: list[dict] = []
    created: list[dict] = []

    unsubs = [
        core.bus.subscribe(topics.CHAT_COMPLETE, lambda e: chat_complete.append(dict(e.payload))),
        core.bus.subscribe(topics.PLAN_REPLAN_REQUEST, lambda e: replan_requests.append(dict(e.payload))),
        core.bus.subscribe(topics.WORKSPACE_CREATED, lambda e: created.append(dict(e.payload))),
        core.bus.subscribe(
            topics.TOOL_CONFIRMATION_REQUIRED,
            lambda e: core.bus.publish(
                topics.TOOL_APPROVED,
                {"confirmation_id": str(e.payload.get("confirmation_id", ""))},
                source="test",
            ),
        ),
    ]

    try:
        core.startup()
        controller.create_workspace("Fallback Workspace", "active workspace")
        assert _wait_for(lambda: bool(created), timeout_s=3.0)
        workspace_id = str(created[-1]["workspace_id"])
        controller.select_workspace(workspace_id)
        time.sleep(0.2)
        initial_complete_count = len(chat_complete)
        core.bus.publish(topics.UI_COMMAND, {"text": "What can you do today?"}, source="test")
        assert _wait_for(lambda: len(chat_complete) > initial_complete_count, timeout_s=8.0)
        payload = chat_complete[-1]
        text = str(payload.get("text", ""))
        assert "calendar not connected" not in text.lower()
        assert "ollama is not running" in text.lower()
        assert not replan_requests
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()
