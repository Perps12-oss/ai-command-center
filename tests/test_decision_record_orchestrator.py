"""ADR-021 Gate 4 — ordinary-path Decision Records (decision_record)."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    DECISION_RECORD_UPDATED,
    EXECUTION_RUN_REQUEST,
    EXECUTION_STEP_AWAITING_APPROVAL,
)
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.db.connection import connect, init_database
from ai_command_center.domain.decision_record import MISSING_MARKER, is_missing
from ai_command_center.repositories.execution_event_repository import ExecutionEventRepository
from ai_command_center.services.execution_event_service import ExecutionEventService
from ai_command_center.services.execution_orchestrator_service import ExecutionOrchestratorService
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry
from tests.support.shell_confirmation import TRUSTED_UI_RUN


def _run_search(bus: EventBus, *, run_id: str, success: bool) -> None:
    def _search(_args: object) -> ToolResult:
        if success:
            return ToolResult(success=True, output="hit:alpha", facts={"query": "alpha"})
        return ToolResult(success=False, output="", error="index down")

    registry = ToolRegistry()
    registry.register_tool(ToolSpec(name="notes.search", description="search", handler=_search))
    ToolExecutorService(bus, registry).start()
    ExecutionOrchestratorService(bus).start()
    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            **TRUSTED_UI_RUN,
            "run_id": run_id,
            "request_id": f"req-{run_id}",
            "auto_approve": True,
            "plan": {
                "goal": "find alpha",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "notes.search",
                        "args": {"query": "alpha"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )


def _assert_record_keys(record: dict) -> None:
    for key in ("evidence", "policy", "receipt", "verification", "summary", "run_id", "step_id"):
        assert key in record, f"omitted Decision Record key: {key}"
        assert record[key] != {}, f"{key} must not use {{}} as missing"


def test_decision_record_emitted_on_successful_tool_step() -> None:
    bus = EventBus()
    records: list[dict] = []
    bus.subscribe(DECISION_RECORD_UPDATED, lambda e: records.append(dict(e.payload)))
    _run_search(bus, run_id="run-ok", success=True)
    completed = [r for r in records if str(r.get("summary", "")).startswith("step completed")]
    assert completed, records
    record = completed[-1]
    _assert_record_keys(record)
    assert record["receipt"].get("success") is True
    assert record["receipt"].get("output") == "hit:alpha"
    assert "completed" in record["summary"]
    assert record["verification"].get("valid") is True


def test_decision_record_emitted_on_failed_tool_step() -> None:
    bus = EventBus()
    records: list[dict] = []
    bus.subscribe(DECISION_RECORD_UPDATED, lambda e: records.append(dict(e.payload)))
    _run_search(bus, run_id="run-fail", success=False)
    failed = [r for r in records if str(r.get("summary", "")).startswith("step failed")]
    assert failed, records
    record = failed[-1]
    _assert_record_keys(record)
    assert record["receipt"].get("success") is False
    assert "failed" in record["summary"]
    assert record["verification"].get("valid") is False


def test_decision_record_history_via_execution_events() -> None:
    bus = EventBus()
    db = init_database(connect(Path(":memory:")))
    repo = ExecutionEventRepository(db)
    ExecutionEventService(bus, repo=repo).start()
    records: list[dict] = []
    bus.subscribe(DECISION_RECORD_UPDATED, lambda e: records.append(dict(e.payload)))
    _run_search(bus, run_id="run-hist", success=True)
    assert records
    events = repo.list_by_request("run-hist")
    kinds = [e.event_type for e in events]
    assert DECISION_RECORD_UPDATED in kinds
    stored = next(e for e in events if e.event_type == DECISION_RECORD_UPDATED)
    payload = stored.payload_dict()
    assert payload.get("step_id") == "s1"


def test_decision_record_awaiting_approval_uses_missing_receipt() -> None:
    bus = EventBus()
    records: list[dict] = []
    awaiting: list[dict] = []
    bus.subscribe(DECISION_RECORD_UPDATED, lambda e: records.append(dict(e.payload)))
    bus.subscribe(EXECUTION_STEP_AWAITING_APPROVAL, lambda e: awaiting.append(dict(e.payload)))
    ExecutionOrchestratorService(bus).start()
    bus.publish(
        EXECUTION_RUN_REQUEST,
        {
            **TRUSTED_UI_RUN,
            "run_id": "run-hitl",
            "plan": {
                "goal": "destroy",
                "steps": [
                    {
                        "step_id": "s1",
                        "capability": "shell",
                        "args": {"command": "echo hi"},
                        "require_approval": False,
                    }
                ],
            },
        },
        source="test",
    )
    assert awaiting
    assert records
    receipt = records[0]["receipt"]
    assert is_missing(receipt) or receipt.get("status") == MISSING_MARKER
