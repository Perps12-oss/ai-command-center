"""UI tests for PR-UI-E10 Evidence Workspace."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_EVIDENCE_OPEN, UI_EVIDENCE_SELECT
from ai_command_center.domain.orchestration_run_snapshot import (
    OrchestrationRunEntry,
    OrchestrationRunSnapshot,
)
from ai_command_center.ui.components.sidebar import NAV_GROUPS
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.shell.view_manager import VIEW_IDS
from tests.ui.fake_ui import ClaimCard, EvidenceView, ReceiptChain, TruthBadge


def _orch() -> OrchestrationRunSnapshot:
    return OrchestrationRunSnapshot(
        request_id="req-1",
        query="Did the deploy succeed?",
        intent="verify_deploy",
        execution_success=True,
        execution_facts=(("status", "ok"), ("env", "prod")),
        truth_valid=True,
        truth_detail="matches expected outcome",
        response_source="ollama",
        receipt_id="rcpt-1",
        trace_id="trace-1",
        span_id="span-1",
        run_history=(
            OrchestrationRunEntry(
                request_id="req-0",
                query="Earlier claim",
                truth_valid=False,
                truth_detail="partial coverage",
                receipt_id="rcpt-0",
                trace_id="trace-0",
            ),
        ),
        total_runs=2,
    )


def test_evidence_registered_in_nav_and_view_ids():
    assert "evidence" in VIEW_IDS
    view_ids = [vid for _, items in NAV_GROUPS for vid, _ in items]
    assert "evidence" in view_ids


def test_evidence_view_projects_claims_and_selection():
    inspected: list[object] = []
    view = EvidenceView(None, on_inspect_select=lambda ref: inspected.append(ref))
    view.apply_state(AppState(orchestration_run=_orch()))
    assert "2 claims" in view._metrics.cget("text")
    assert len(view._claims_scroll.winfo_children()) >= 2

    view._select("req-1")
    assert view._selected_request_id == "req-1"
    assert inspected and getattr(inspected[-1], "kind") == "evidence"
    payload = dict(getattr(inspected[-1], "payload"))
    assert payload.get("receipt_id") == "rcpt-1"
    assert payload.get("trace_id") == "trace-1"
    assert "VALID" in view._truth._badge.cget("text") or "valid" in view._truth._badge.cget("text").lower()


def test_evidence_components():
    selected: list[str] = []
    ClaimCard(
        None,
        request_id="r1",
        claim_text="Claim",
        truth_state="valid",
        on_select=lambda rid: selected.append(rid),
    )._click()
    assert selected == ["r1"]
    badge = TruthBadge(None)
    badge.set_state("failed")
    assert "FAILED" in badge.cget("text")
    chain = ReceiptChain(None)
    chain.apply_entry(
        OrchestrationRunEntry(
            request_id="r1",
            receipt_id="rc",
            trace_id="t",
            span_id="s",
            execution_facts=(("k", "v"),),
        )
    )


def test_controller_evidence_intents():
    bus = EventBus()
    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[str] = []
    bus.subscribe(UI_EVIDENCE_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_EVIDENCE_OPEN, lambda e: seen.append(e.topic))
    controller.publish_evidence_select("req-1")
    controller.publish_evidence_open()
    assert seen == [UI_EVIDENCE_SELECT, UI_EVIDENCE_OPEN]
