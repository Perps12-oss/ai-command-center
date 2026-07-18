"""Projection tests for Phase 11C Execution Center workspace."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.app_state import AppState
from ai_command_center.core.state.execution_event_state import (
    ExecutionEventItem,
    ExecutionScrubberState,
)
from ai_command_center.core.state.execution_state import ExecutionContext
from ai_command_center.domain.execution_library_snapshot import (
    ExecutionLibrarySnapshot,
    ExecutionPlanSnapshot,
    ExecutionRunEntry,
    ExecutionStepSnapshot,
)
from ai_command_center.domain.orchestration_run_snapshot import OrchestrationRunSnapshot
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.execution_center.execution_list_panel import (
    sort_execution_rows,
)
from ai_command_center.ui.views.execution_center.truth_validation_panel import (
    truth_state_for_entry,
)
from tests.ui.fake_ui import ExecutionsView

ROOT = Path(__file__).resolve().parents[2]


def _sample_snap(
    *,
    active: bool = True,
    receipt: bool = True,
    truth_valid: bool = True,
    truth_detail: str = "verified",
) -> AppState:
    plan = ExecutionPlanSnapshot(
        run_id="run-1",
        request_id="req-1",
        goal="Ship feature",
        total_steps=2,
        status="running" if active else "complete",
        current_step_id="s1",
        steps=(
            ExecutionStepSnapshot(step_id="s1", run_id="run-1", index=0, capability="plan", status="running"),
            ExecutionStepSnapshot(step_id="s2", run_id="run-1", index=1, capability="apply", status="waiting"),
        ),
    )
    history = (
        ExecutionRunEntry(
            run_id="run-1",
            request_id="req-1",
            source="orchestration",
            created_at=1_700_000_000.0,
            summary="Ship feature",
            status="running" if active else "complete",
        ),
        ExecutionRunEntry(
            run_id="run-2",
            request_id="req-2",
            source="chat",
            created_at=1_700_000_100.0,
            summary="Failed job",
            status="failed",
        ),
        ExecutionRunEntry(
            run_id="run-3",
            request_id="req-3",
            source="agent",
            created_at=1_700_000_200.0,
            summary="Done job",
            status="complete",
        ),
    )
    orch = OrchestrationRunSnapshot(
        request_id="req-1",
        query="Ship feature",
        provider_id="ollama",
        execution_success=True,
        execution_facts=(("step", "1"), ("ok", "true")),
        truth_valid=truth_valid,
        truth_detail=truth_detail,
        response_source="ollama",
        receipt_id="rcpt-1" if receipt else "",
    )
    return AppState(
        execution_library=ExecutionLibrarySnapshot(
            active_plan=plan,
            run_history=history,
            total_runs=3,
        ),
        execution_context=ExecutionContext(
            request_id="req-1",
            provider_id="ollama",
            model="llama",
            status="running" if active else "complete",
            intent="execute",
            query="Ship feature",
        ),
        execution_scrubber=ExecutionScrubberState(
            request_id="req-1",
            events=(
                ExecutionEventItem(event_id="e1", request_id="req-1", event_type="step.start", scope="plan"),
                ExecutionEventItem(event_id="e2", request_id="req-1", event_type="step.wait", scope="apply"),
            ),
            scrub_index=1,
            source="runs",
        ),
        orchestration_run=orch,
    )


def test_hero_metrics_and_active_action() -> None:
    selected: list[str] = []
    view = ExecutionsView(None, on_select=selected.append)
    view.apply_state(_sample_snap(active=True))

    metrics = view._metrics.cget("text")
    assert "1 active" in metrics
    assert "3 total" in metrics
    assert "1 failed" in metrics
    assert "success" in metrics
    assert view._hero_action.cget("text") == "View Active Execution"
    view._hero_action.invoke()
    assert selected == ["req-1"]


def test_hero_opens_latest_when_idle() -> None:
    selected: list[str] = []
    view = ExecutionsView(None, on_select=selected.append)
    view.apply_state(_sample_snap(active=False))
    assert view._hero_action.cget("text") == "Open Latest Execution"
    assert str(view._hero_action.cget("state")) == "normal"
    view._hero_action.invoke()
    assert selected  # latest from library


def test_hero_disabled_when_no_executions() -> None:
    selected: list[str] = []
    view = ExecutionsView(None, on_select=selected.append)
    view.apply_state(AppState())
    assert view._hero_action.cget("text") == "No Executions"
    assert str(view._hero_action.cget("state")) == "disabled"
    view._on_hero_action()
    assert selected == []
    banner = view._surface_state.cget("text")
    assert "Next" in banner
    assert "execution" in banner.lower()


def test_surface_state_loading_none_snapshot() -> None:
    view = ExecutionsView(None)
    view.apply_state(None)
    assert "Loading" in view._surface_state.cget("text")
    assert str(view._hero_action.cget("state")) == "disabled"


def test_list_sort_failures_first() -> None:
    from ai_command_center.ui.views.execution_center.execution_list_panel import _RunRow

    rows = [
        _RunRow("c", "c", "g", "complete", "chat", 3.0, "1s", ""),
        _RunRow("f", "f", "g", "failed", "chat", 2.0, "1s", ""),
        _RunRow("a", "a", "g", "running", "chat", 1.0, "1s", ""),
        _RunRow("w", "w", "g", "waiting", "chat", 0.0, "1s", ""),
    ]
    ordered = [r.status for r in sort_execution_rows(rows)]
    assert ordered == ["running", "failed", "waiting", "complete"]


def test_selection_updates_detail_and_receipt() -> None:
    view = ExecutionsView(None, on_select=lambda _i: None)
    snap = _sample_snap(receipt=True)
    view.apply_state(snap)
    view._select("req-1")

    detail_texts: list[str] = []
    for child in view._detail._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    detail_texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    assert any("req-1" in t for t in detail_texts)
    assert any("Ship feature" in t for t in detail_texts)

    receipt_texts: list[str] = []
    for child in view._receipt._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    receipt_texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    assert any("rcpt-1" in t for t in receipt_texts)


def test_missing_receipt_handled() -> None:
    view = ExecutionsView(None)
    view.apply_state(_sample_snap(receipt=False))
    view._select("req-1")
    texts = []
    for child in view._receipt._body.winfo_children():
        if hasattr(child, "cget"):
            try:
                texts.append(str(child.cget("text")))
            except Exception:
                pass
    assert any("No receipt" in t for t in texts)


def test_truth_validation_states() -> None:
    valid = OrchestrationRunSnapshot(request_id="r", truth_valid=True, truth_detail="ok", receipt_id="x")
    partial = OrchestrationRunSnapshot(
        request_id="r", truth_valid=False, truth_detail="partial match", receipt_id="x"
    )
    failed = OrchestrationRunSnapshot(request_id="r", truth_valid=False, truth_detail="mismatch", receipt_id="x")
    assert truth_state_for_entry(valid) == "valid"
    assert truth_state_for_entry(partial) == "partial"
    assert truth_state_for_entry(failed) == "failed"

    view = ExecutionsView(None)
    view.apply_state(_sample_snap(truth_valid=True, truth_detail="verified"))
    view._select("req-1")
    assert "VALID" in str(view._truth._badge.cget("text")).upper()

    view.apply_state(_sample_snap(truth_valid=False, truth_detail="partial evidence"))
    view._select("req-1")
    assert "PARTIAL" in str(view._truth._badge.cget("text")).upper()

    view.apply_state(_sample_snap(truth_valid=False, truth_detail="failed check"))
    view._select("req-1")
    assert "FAILED" in str(view._truth._badge.cget("text")).upper()


def test_timeline_scrub_callback() -> None:
    scrubbed: list[tuple[str, int]] = []
    view = ExecutionsView(None, on_scrub=lambda rid, i: scrubbed.append((rid, i)))
    view.apply_state(_sample_snap())
    view._select("req-1")
    view._scrub(1)
    assert scrubbed == [("req-1", 1)]


def test_execution_blue_token_used() -> None:
    files = [
        ROOT / "ai_command_center/ui/views/executions_view.py",
        ROOT / "ai_command_center/ui/views/execution_center/execution_list_panel.py",
        ROOT / "ai_command_center/ui/views/execution_center/execution_timeline_panel.py",
        ROOT / "ai_command_center/ui/views/execution_center/execution_detail_panel.py",
        ROOT / "ai_command_center/ui/views/execution_center/receipt_viewer_panel.py",
        ROOT / "ai_command_center/ui/views/execution_center/truth_validation_panel.py",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "EXECUTION_BLUE" in text, path.name
        assert "#3B82F6" not in text or "theme" in path.name, path.name
    assert T.EXECUTION_BLUE == "#3B82F6"


def test_no_repo_or_service_imports() -> None:
    text = (ROOT / "ai_command_center/ui/views/executions_view.py").read_text(encoding="utf-8")
    assert "ai_command_center.repositories" not in text
    assert "ai_command_center.services" not in text
    assert "add_listener" not in text
