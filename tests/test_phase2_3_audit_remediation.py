"""Phase 2+3 adversarial-audit remediation regression tests."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.command_sandbox import (
    ORCHESTRATION_SHELL_ALLOWLIST,
    CommandSandbox,
    READONLY_COMMAND_SANDBOX,
    SecurityError,
)
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.dispatch_policy import (
    ASYNC_ELIGIBLE_TOPICS,
    SYNC_CRITICAL_TOPICS,
)
from ai_command_center.core.events.topics import (
    EXECUTION_AUTHORITY_DECISION,
    EXECUTION_RUNS_LOADED,
    GOAL_SUBMIT_REQUEST,
    SETTINGS_ERROR,
    SETTINGS_UPDATED,
    UI_COMMAND,
    UI_COMMAND_REPLAY,
    UI_CREATE_WORKSPACE,
    UI_WORKSPACE_REQUIRED,
    WORKSPACE_ACTIVE,
)
from ai_command_center.core.settings.settings_schema import SettingsSchema
from ai_command_center.core.settings.settings_service import SettingsService as CoreSettingsService
from ai_command_center.db.connection import connect, init_database
from ai_command_center.domain.execution import Execution, ExecutionStatus
from ai_command_center.orchestration.providers.shell_provider import _default_run
from ai_command_center.repositories.settings_repository import SettingsRepository
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.execution_run_service import ExecutionRunService
from ai_command_center.services.workspace_bootstrap_service import WorkspaceBootstrapService


def _wait_until(predicate, *, timeout_s: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


# ---------------------------------------------------------------------------
# B5 — request_id continuity
# ---------------------------------------------------------------------------


def test_execution_authority_reuses_payload_request_id() -> None:
    bus = EventBus()
    authority = ExecutionAuthorityService(bus)
    decisions: list[dict] = []
    goals: list[dict] = []
    bus.subscribe(EXECUTION_AUTHORITY_DECISION, lambda e: decisions.append(dict(e.payload)))
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: goals.append(dict(e.payload)))
    authority.load()
    try:
        bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-corr"}, source="test")
        bus.publish(
            UI_COMMAND,
            {"text": "hello correlation", "request_id": "req-preserve-1234"},
            source="test",
        )
        assert decisions
        assert decisions[-1]["request_id"] == "req-preserve-1234"
        assert goals
        assert goals[-1]["request_id"] == "req-preserve-1234"
    finally:
        authority.unload()


def test_bootstrap_replay_preserves_request_id_into_authority() -> None:
    bus = EventBus()
    bootstrap = WorkspaceBootstrapService(bus)
    authority = ExecutionAuthorityService(bus)
    decisions: list[dict] = []
    bus.subscribe(EXECUTION_AUTHORITY_DECISION, lambda e: decisions.append(dict(e.payload)))
    bootstrap.start()
    authority.load()
    try:
        bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-1"}, source="test")
        bus.publish(
            UI_WORKSPACE_REQUIRED,
            {"request_id": "req-replay-abcd", "text": "summarize notes"},
            source="test",
        )
        assert _wait_until(lambda: any(d.get("request_id") == "req-replay-abcd" for d in decisions))
    finally:
        authority.unload()
        bootstrap.stop()


# ---------------------------------------------------------------------------
# B6 — async replay envelope
# ---------------------------------------------------------------------------


def test_ui_command_replay_is_async_eligible_not_sync_critical() -> None:
    assert UI_COMMAND in SYNC_CRITICAL_TOPICS
    assert UI_COMMAND_REPLAY in ASYNC_ELIGIBLE_TOPICS
    assert UI_COMMAND_REPLAY not in SYNC_CRITICAL_TOPICS


def test_bootstrap_publishes_replay_envelope_not_nested_ui_command_directly() -> None:
    bus = EventBus()
    service = WorkspaceBootstrapService(bus)
    replays: list[dict] = []
    commands: list[dict] = []
    bus.subscribe(UI_COMMAND_REPLAY, lambda e: replays.append(dict(e.payload)))
    # Capture UI_COMMAND without consuming the bootstrap's own promotion handler.
    bus.subscribe(UI_COMMAND, lambda e: commands.append(dict(e.payload)))
    service.start()
    try:
        bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-async"}, source="test")
        bus.publish(
            UI_WORKSPACE_REQUIRED,
            {"request_id": "req-async-1", "text": "ping"},
            source="test",
        )
        assert len(replays) == 1
        assert replays[0]["request_id"] == "req-async-1"
        # Bare EventBus delivers ASYNC_ELIGIBLE inline → promotion still happens.
        assert any(c.get("request_id") == "req-async-1" for c in commands)
    finally:
        service.stop()


# ---------------------------------------------------------------------------
# Duplicate deferred-command idempotency
# ---------------------------------------------------------------------------


def test_duplicate_workspace_required_same_request_id_replays_once() -> None:
    bus = EventBus()
    service = WorkspaceBootstrapService(bus)
    commands: list[dict] = []
    creates: list[dict] = []
    bus.subscribe(UI_COMMAND, lambda e: commands.append(dict(e.payload)))
    bus.subscribe(UI_CREATE_WORKSPACE, lambda e: creates.append(dict(e.payload)))
    service.start()
    try:
        bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-dedupe"}, source="test")
        for _ in range(3):
            bus.publish(
                UI_WORKSPACE_REQUIRED,
                {"request_id": "req-dedupe-1", "text": "same command"},
                source="test",
            )
        assert len(commands) == 1
        assert not creates
    finally:
        service.stop()


# ---------------------------------------------------------------------------
# B7 / B8 — sandbox policy
# ---------------------------------------------------------------------------


def test_readonly_shell_rejects_unrestricted_file_readers() -> None:
    with pytest.raises(SecurityError):
        READONLY_COMMAND_SANDBOX.validate_command("cat /etc/passwd")
    with pytest.raises(SecurityError):
        READONLY_COMMAND_SANDBOX.validate_command(r"type C:\secret\app.db")
    assert READONLY_COMMAND_SANDBOX.validate_command("echo ok")


def test_default_sandbox_rejects_git_config_and_python_scripts() -> None:
    sandbox = CommandSandbox()
    with pytest.raises(SecurityError):
        sandbox.validate_command("git config --global core.fsmonitor calc")
    with pytest.raises(SecurityError):
        sandbox.validate_command("git config --global alias.x !calc")
    with pytest.raises(SecurityError):
        sandbox.validate_command("python evil.py")
    assert sandbox.validate_command("git status")


def test_shell_provider_uses_orchestration_allowlist() -> None:
    assert "python" not in ORCHESTRATION_SHELL_ALLOWLIST
    result = _default_run("git config user.name attacker")
    assert result["success"] is False
    result_ok = _default_run("echo hello")
    assert result_ok["success"] is True


# ---------------------------------------------------------------------------
# B9 — settings validation rejection
# ---------------------------------------------------------------------------


def test_settings_invalid_value_publishes_error_and_does_not_write() -> None:
    bus = EventBus()
    db = init_database(connect(Path(":memory:")))
    repo = SettingsRepository(db)
    schema = SettingsSchema()
    service = CoreSettingsService(repo, schema, bus=bus)
    errors: list[dict] = []
    updates: list[dict] = []
    bus.subscribe(SETTINGS_ERROR, lambda e: errors.append(dict(e.payload)))
    bus.subscribe(SETTINGS_UPDATED, lambda e: updates.append(dict(e.payload)))
    before = repo.get("window_width", "")
    with pytest.raises((TypeError, ValueError)):
        service.set("window_width", "not-an-int")
    assert errors
    assert errors[-1]["key"] == "window_width"
    assert not updates
    assert repo.get("window_width", "") == before


# ---------------------------------------------------------------------------
# B14 — success attribution on rehydration
# ---------------------------------------------------------------------------


def test_execution_from_orchestration_payload_maps_failure() -> None:
    exe = Execution.from_orchestration_payload(
        {
            "request_id": "r1",
            "query": "q",
            "execution_success": False,
            "execution_error": "provider down",
            "truth_valid": True,
        }
    )
    assert exe.status is ExecutionStatus.FAILED
    assert exe.error == "provider down"


def test_execution_run_rehydration_preserves_success_status() -> None:
    bus = EventBus()
    db = init_database(connect(Path(":memory:")))
    from ai_command_center.repositories.execution_run_repository import ExecutionRunRepository

    repo = ExecutionRunRepository(db)
    repo.append(
        request_id="run-fail-1",
        source="orchestration",
        snapshot={
            "request_id": "run-fail-1",
            "query": "need provider",
            "execution_success": False,
            "truth_valid": True,
            "truth_detail": "execution run completed",
        },
    )
    loaded: list[dict] = []
    bus.subscribe(EXECUTION_RUNS_LOADED, lambda e: loaded.append(dict(e.payload)))
    store = AppStateStore(bus)
    service = ExecutionRunService(bus, repo=repo)
    service.start()
    try:
        assert loaded
        runs = loaded[-1]["runs"]
        assert runs
        entry = next(r for r in runs if r["request_id"] == "run-fail-1")
        assert entry["status"] == "error"
        assert entry["success"] is False
        assert entry["summary"] == "need provider"
        # AppState consumes supplied status rather than hardcoding complete.
        lib = store.snapshot.execution_library
        match = next((r for r in lib.run_history if r.request_id == "run-fail-1"), None)
        assert match is not None
        assert match.status == "error"
    finally:
        service.stop()
