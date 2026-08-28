"""Regression tests for the Phase 1 boundary repair.

Each test reproduces a confirmed defect where bad state could become
authoritative state (audit clusters 1-3):

* provider unavailable was receipted as a *successful* LLM answer;
* provider readiness was non-replayable shadow state (restart wedged it);
* teardown could hang forever, or drop an outcome while keeping its receipt;
* one orchestrated answer was persisted twice.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from ai_command_center.application import create_application
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events import topics
from ai_command_center.db.conn_sync import ConnectionCloseTimeout, GuardedConnection
from ai_command_center.db.connection import connect, init_database
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.ollama_http_service import OllamaHttpService
from ai_command_center.ui.workspace_os_controller import WorkspaceOsUIController


def _wait_for(predicate, timeout_s: float = 8.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def _approve_tools(core) -> None:
    core.bus.subscribe(
        topics.TOOL_CONFIRMATION_REQUIRED,
        lambda e: core.bus.publish(
            topics.TOOL_APPROVED,
            {"confirmation_id": str(e.payload.get("confirmation_id", ""))},
            source="test",
        ),
    )


def _active_workspace(core, controller: WorkspaceOsUIController, title: str) -> str:
    created: list[dict] = []
    core.bus.subscribe(topics.WORKSPACE_CREATED, lambda e: created.append(dict(e.payload)))
    controller.create_workspace(title, "active workspace")
    assert _wait_for(lambda: bool(created), timeout_s=4.0)
    workspace_id = str(created[-1]["workspace_id"])
    controller.select_workspace(workspace_id)
    return workspace_id


def test_provider_unavailable_fails_the_run_instead_of_completing_it() -> None:
    """B1: an unavailable provider must not produce a successful LLM answer."""
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    controller = WorkspaceOsUIController(core.bus)
    capability_complete: list[dict] = []
    capability_error: list[dict] = []
    receipts: list[dict] = []
    chat_complete: list[dict] = []
    unsubs = [
        core.bus.subscribe(
            topics.CAPABILITY_COMPLETE, lambda e: capability_complete.append(dict(e.payload))
        ),
        core.bus.subscribe(
            topics.CAPABILITY_ERROR, lambda e: capability_error.append(dict(e.payload))
        ),
        core.bus.subscribe(
            topics.ORCHESTRATION_RECEIPT, lambda e: receipts.append(dict(e.payload))
        ),
        core.bus.subscribe(topics.CHAT_COMPLETE, lambda e: chat_complete.append(dict(e.payload))),
    ]
    try:
        core.startup()
        _approve_tools(core)
        _active_workspace(core, controller, "Unavailable Provider Workspace")
        core.bus.publish(
            topics.OLLAMA_STATUS,
            {"online": False, "detail": "connection refused", "url": "http://localhost:11434"},
            source="test",
        )
        start = len(chat_complete)
        core.bus.publish(
            topics.UI_COMMAND,
            {"text": "Explain quantum entanglement."},
            source="test",
        )
        assert _wait_for(lambda: len(chat_complete) > start)

        llm_completes = [p for p in capability_complete if p.get("capability") == "llm"]
        llm_errors = [p for p in capability_error if p.get("capability") == "llm"]
        assert not llm_completes, "unavailable provider must not complete the llm step"
        assert llm_errors, "unavailable provider must fail the llm step"
        assert llm_errors[-1].get("reason") == "provider_unavailable"

        assert receipts, "expected a receipt for the run"
        assert receipts[-1].get("success") is False
        assert chat_complete[-1].get("truth_validated") is False
        # The explanation still reaches the user — as failure information.
        assert "i need an ai provider to answer that" in str(
            chat_complete[-1].get("text", "")
        ).lower()
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()


def test_ollama_service_reannounces_status_on_query() -> None:
    """B2/B11: the provider owner replays readiness for an empty projection."""
    bus = EventBus()
    service = OllamaHttpService(bus)
    bus.subscribe(topics.PROVIDER_STATUS_QUERY, service._on_status_query)
    replays: list[dict] = []
    bus.subscribe(
        topics.OLLAMA_STATUS,
        lambda e: replays.append(dict(e.payload)) if e.payload.get("reannounced") else None,
    )

    # Nothing known yet: a query must not invent a status.
    bus.publish(topics.PROVIDER_STATUS_QUERY, {"provider": "ollama"}, source="test")
    assert not replays

    service._last_status_key = (True, "")
    bus.publish(topics.PROVIDER_STATUS_QUERY, {"provider": "ollama"}, source="test")
    assert replays and replays[-1]["online"] is True

    replays.clear()
    bus.publish(topics.PROVIDER_STATUS_QUERY, {"provider": "openai"}, source="test")
    assert not replays, "a query for another provider must be ignored"


def _run_llm_step(bus: EventBus, request_id: str) -> None:
    bus.publish(
        topics.LLM_STEP_REQUEST,
        {
            "request_id": request_id,
            "run_id": f"run-{request_id}",
            "step_id": "step-1",
            "capability": "llm",
            "args": {"prompt": "Explain quantum entanglement."},
        },
        source="test",
    )


def test_healthy_provider_survives_chat_handler_restart() -> None:
    """B2/B11: readiness is reconciled with the owner, not lost on restart."""
    bus = EventBus()
    llm_requests: list[dict] = []
    capability_errors: list[dict] = []
    bus.subscribe(topics.LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    bus.subscribe(topics.CAPABILITY_ERROR, lambda e: capability_errors.append(dict(e.payload)))

    # Stand in for the provider owner: it alone answers readiness queries, and
    # it announced healthy before the handler ever subscribed.
    def _owner(event) -> None:
        requested = str(event.payload.get("provider", "")).strip().lower()
        if requested and requested != "ollama":
            return
        bus.publish(
            topics.OLLAMA_STATUS,
            {"online": True, "detail": "", "url": "http://localhost:11434", "reannounced": True},
            source="provider_owner",
        )

    bus.subscribe(topics.PROVIDER_STATUS_QUERY, _owner)

    handler = ChatHandlerService(bus, ContextManager(max_context_tokens=4096))
    handler.start()
    try:
        _run_llm_step(bus, "rq-1")
        assert not capability_errors, "a healthy provider must not read as unavailable"
        assert len(llm_requests) == 1

        handler.stop()
        handler.start()

        _run_llm_step(bus, "rq-2")
        assert not capability_errors, (
            "a restarted handler must reconcile readiness with the provider owner"
        )
        assert len(llm_requests) == 2
    finally:
        handler.stop()


def test_shutdown_still_delivers_outcome_topics() -> None:
    """B13: a receipt must not survive while its outcome is dropped."""
    bus = EventBus(async_dispatch=True)
    outcomes: list[str] = []
    chunks: list[str] = []
    bus.subscribe(topics.TOOL_RESULT, lambda e: outcomes.append(str(e.topic)))
    bus.subscribe(topics.CHAT_CHUNK, lambda e: chunks.append(str(e.topic)))

    assert bus.shutdown() is True

    delivered = bus.publish(topics.TOOL_RESULT, {"tool": "shell"}, source="test")
    dropped = bus.publish(topics.CHAT_CHUNK, {"text": "partial"}, source="test")

    assert outcomes == [topics.TOOL_RESULT]
    assert delivered.delivery == "delivered"
    assert not chunks
    assert dropped.delivery == "dropped"


def test_close_is_bounded_when_another_thread_holds_a_transaction() -> None:
    """B4: an open transaction must not hang shutdown forever."""
    raw = sqlite3.connect(":memory:", check_same_thread=False)
    conn = GuardedConnection(raw)
    conn.execute("CREATE TABLE t (v INTEGER)")
    conn.commit()

    holding = threading.Event()
    release = threading.Event()

    def _hold() -> None:
        conn.execute("INSERT INTO t (v) VALUES (1)")  # opens a transaction
        holding.set()
        release.wait(10.0)
        conn.rollback()

    worker = threading.Thread(target=_hold, daemon=True)
    worker.start()
    assert holding.wait(5.0)

    started = time.monotonic()
    with pytest.raises(ConnectionCloseTimeout):
        conn.close(timeout=0.2)
    elapsed = time.monotonic() - started
    assert elapsed < 5.0, "close must give up rather than block indefinitely"

    release.set()
    worker.join(5.0)
    conn.close(timeout=2.0)


def test_one_orchestrated_response_persists_one_assistant_message() -> None:
    """B12: duplicate assistant rows double-weight the answer in later context."""
    db = init_database(connect(Path(":memory:")))
    core = create_application(db=db)
    controller = WorkspaceOsUIController(core.bus)
    chat_complete: list[dict] = []
    unsubs = [
        core.bus.subscribe(topics.CHAT_COMPLETE, lambda e: chat_complete.append(dict(e.payload))),
    ]
    try:
        core.startup()
        _approve_tools(core)
        _active_workspace(core, controller, "Persistence Workspace")
        start = len(chat_complete)
        core.bus.publish(topics.UI_COMMAND, {"text": "What time is it?"}, source="test")
        assert _wait_for(lambda: len(chat_complete) > start)
        text = str(chat_complete[-1].get("text", "")).strip()
        assert text

        time.sleep(0.3)
        rows = db.execute(
            "SELECT content FROM messages WHERE role = 'assistant'"
        ).fetchall()
        matching = [r for r in rows if str(r[0]).strip() == text]
        assert len(matching) == 1, f"expected exactly one assistant row, got {len(matching)}"
    finally:
        for unsub in unsubs:
            unsub()
        core.shutdown()
