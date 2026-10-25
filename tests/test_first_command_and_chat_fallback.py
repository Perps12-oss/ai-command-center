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


def test_deterministic_time_query_works_without_provider() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    controller = WorkspaceOsUIController(core.bus)
    llm_requests: list[dict] = []
    chat_complete: list[dict] = []
    created: list[dict] = []
    unsubs = [
        core.bus.subscribe(topics.LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload))),
        core.bus.subscribe(topics.CHAT_COMPLETE, lambda e: chat_complete.append(dict(e.payload))),
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
        controller.create_workspace("Deterministic Workspace", "active workspace")
        assert _wait_for(lambda: bool(created), timeout_s=3.0)
        controller.select_workspace(str(created[-1]["workspace_id"]))
        start = len(chat_complete)
        core.bus.publish(topics.UI_COMMAND, {"text": "What time is it?"}, source="test")
        assert _wait_for(lambda: len(chat_complete) > start, timeout_s=8.0)
        assert not llm_requests
        answer = str(chat_complete[-1].get("text", "")).lower()
        assert "utc" in answer or "coordinated universal time" in answer
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
        assert "i need an ai provider to answer that" in text.lower()
        assert "[set up ollama]" in text.lower()
        assert not replan_requests
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()


def test_llm_request_uses_configured_provider_when_ready() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    controller = WorkspaceOsUIController(core.bus)
    llm_requests: list[dict] = []
    created: list[dict] = []
    unsubs = [
        core.bus.subscribe(topics.LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload))),
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
        controller.create_workspace("Provider Ready Workspace", "active workspace")
        assert _wait_for(lambda: bool(created), timeout_s=3.0)
        controller.select_workspace(str(created[-1]["workspace_id"]))
        core.bus.publish(
            topics.OLLAMA_STATUS,
            {"online": True, "detail": "", "url": "http://localhost:11434"},
            source="test",
        )
        core.bus.publish(
            topics.UI_COMMAND,
            {"text": "Explain quantum entanglement."},
            source="test",
        )
        assert _wait_for(lambda: bool(llm_requests), timeout_s=3.0)
        assert str(llm_requests[-1].get("provider", "")) == "ollama"
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()


def test_llm_request_blocked_when_provider_unavailable() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    controller = WorkspaceOsUIController(core.bus)
    llm_requests: list[dict] = []
    chat_complete: list[dict] = []
    created: list[dict] = []
    unsubs = [
        core.bus.subscribe(topics.LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload))),
        core.bus.subscribe(topics.CHAT_COMPLETE, lambda e: chat_complete.append(dict(e.payload))),
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
        controller.create_workspace("Provider Unavailable Workspace", "active workspace")
        assert _wait_for(lambda: bool(created), timeout_s=3.0)
        controller.select_workspace(str(created[-1]["workspace_id"]))
        core.bus.publish(
            topics.OLLAMA_STATUS,
            {"online": False, "detail": "connection refused", "url": "http://localhost:11434"},
            source="test",
        )
        start = len(chat_complete)
        core.bus.publish(topics.UI_COMMAND, {"text": "Explain quantum entanglement."}, source="test")
        assert _wait_for(lambda: len(chat_complete) > start, timeout_s=8.0)
        assert not llm_requests
        text = str(chat_complete[-1].get("text", "")).lower()
        assert "i need an ai provider to answer that" in text
        assert "[set up ollama]" in text
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()


def test_fresh_first_run_blocks_llm_without_provider_status() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    controller = WorkspaceOsUIController(core.bus)
    llm_requests: list[dict] = []
    chat_complete: list[dict] = []
    created: list[dict] = []
    unsubs = [
        core.bus.subscribe(topics.LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload))),
        core.bus.subscribe(topics.CHAT_COMPLETE, lambda e: chat_complete.append(dict(e.payload))),
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
        controller.create_workspace("Fresh Run Workspace", "active workspace")
        assert _wait_for(lambda: bool(created), timeout_s=3.0)
        controller.select_workspace(str(created[-1]["workspace_id"]))
        start = len(chat_complete)
        core.bus.publish(topics.UI_COMMAND, {"text": "Explain quantum entanglement."}, source="test")
        assert _wait_for(lambda: len(chat_complete) > start, timeout_s=8.0)
        assert not llm_requests
        text = str(chat_complete[-1].get("text", "")).lower()
        assert "i need an ai provider to answer that" in text
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()


def test_configured_provider_remains_authoritative() -> None:
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    controller = WorkspaceOsUIController(core.bus)
    llm_requests: list[dict] = []
    chat_complete: list[dict] = []
    created: list[dict] = []
    unsubs = [
        core.bus.subscribe(topics.LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload))),
        core.bus.subscribe(topics.CHAT_COMPLETE, lambda e: chat_complete.append(dict(e.payload))),
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
        controller.create_workspace("Configured Provider Workspace", "active workspace")
        assert _wait_for(lambda: bool(created), timeout_s=3.0)
        controller.select_workspace(str(created[-1]["workspace_id"]))
        core.bus.publish(
            topics.SETTINGS_SET_REQUEST,
            {"key": "provider", "value": "openai"},
            source="test",
        )
        core.bus.publish(
            topics.OLLAMA_STATUS,
            {"online": True, "detail": "", "url": "http://localhost:11434"},
            source="test",
        )
        core.bus.publish(
            topics.OPENAI_STATUS,
            {"online": False, "configured": False, "detail": "api key not configured"},
            source="test",
        )
        start = len(chat_complete)
        core.bus.publish(topics.UI_COMMAND, {"text": "Explain quantum entanglement."}, source="test")
        assert _wait_for(lambda: len(chat_complete) > start, timeout_s=8.0)
        assert not llm_requests
        text = str(chat_complete[-1].get("text", "")).lower()
        assert "[set up openai]" in text
        assert "ollama" not in text
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()
