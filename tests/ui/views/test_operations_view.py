"""UI tests for PR-UI-E11 Mission Control Operations."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_OPERATION_OPEN,
    UI_OPERATION_SCRUB,
    UI_OPERATION_SELECT,
)
from ai_command_center.core.state.execution_event_state import (
    ExecutionEventItem,
    ExecutionScrubberState,
)
from ai_command_center.domain.agent_pipeline_snapshot import AgentPipelineSnapshot
from ai_command_center.domain.journal_entry import JournalEntry, JournalEntryKind
from ai_command_center.domain.operation_snapshot import OperationSnapshot
from ai_command_center.domain.orchestration_run_snapshot import OrchestrationRunSnapshot
from ai_command_center.ui.components.operations import resolve_active_stage_index
from ai_command_center.ui.components.sidebar import NAV_GROUPS
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.shell.view_manager import VIEW_IDS
from tests.ui.fake_ui import OperationCard, OperationsView


def _snap() -> AppState:
    return AppState(
        operation_library_index=(
            OperationSnapshot(
                correlation_id="corr-1",
                goal_title="Ship E11",
                goal_status="active",
            ),
        ),
        active_operation=OperationSnapshot(
            correlation_id="corr-1",
            goal_title="Ship E11",
            goal_status="active",
        ),
        operation_journal=(
            JournalEntry(
                entry_id=1,
                correlation_id="corr-1",
                kind=JournalEntryKind.PLAN_GENERATED,
                summary="Plan ready",
            ),
            JournalEntry(
                entry_id=2,
                correlation_id="corr-1",
                kind=JournalEntryKind.EXECUTION_STEP,
                summary="Execute step",
            ),
        ),
        agent_pipeline=AgentPipelineSnapshot(
            pipeline_id="pipe-1",
            pipeline_stage="execute",
        ),
        orchestration_run=OrchestrationRunSnapshot(
            request_id="req-1",
            receipt_id="",
            truth_valid=False,
        ),
        execution_scrubber=ExecutionScrubberState(
            request_id="req-1",
            events=(
                ExecutionEventItem(event_id="e1", event_type="start", request_id="req-1"),
            ),
            scrub_index=0,
        ),
    )


def test_operations_registered_in_nav_and_view_ids():
    assert "operations" in VIEW_IDS
    view_ids = [vid for _, items in NAV_GROUPS for vid, _ in items]
    assert "operations" in view_ids


def test_operations_view_stages_timeline_and_scrub_inspect():
    inspected: list[object] = []
    scrubbed: list[tuple[int, dict]] = []
    view = OperationsView(
        None,
        on_scrub=lambda i, step: scrubbed.append((i, step)),
        on_inspect_select=lambda ref: inspected.append(ref),
    )
    view.apply_state(_snap())
    assert "1 operations" in view._metrics.cget("text")
    assert "Executor" in view._stages._hint.cget("text") or "execute" in view._stages._hint.cget("text").lower()
    assert len(view._timeline_steps) >= 2

    view._handle_scrub(1)
    assert scrubbed and scrubbed[-1][0] == 1
    assert inspected and getattr(inspected[-1], "kind") == "execution_event"

    view._select_operation("corr-1")
    assert any(getattr(r, "kind", "") == "operation" for r in inspected)


def test_stage_resolver_and_operation_card():
    assert resolve_active_stage_index(pipeline_stage="planner") == 0
    assert resolve_active_stage_index(pipeline_stage="router") == 1
    assert resolve_active_stage_index(has_receipt=True, truth_valid=True) == 4
    selected: list[str] = []
    OperationCard(
        None,
        correlation_id="c1",
        title="Op",
        on_select=lambda cid: selected.append(cid),
    )._click()
    assert selected == ["c1"]


def test_controller_operation_intents():
    bus = EventBus()
    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[str] = []
    bus.subscribe(UI_OPERATION_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_OPERATION_SCRUB, lambda e: seen.append(e.topic))
    bus.subscribe(UI_OPERATION_OPEN, lambda e: seen.append(e.topic))
    controller.publish_operation_select("corr-1")
    controller.publish_operation_scrub(2, request_id="req-1")
    controller.publish_operation_open()
    assert seen == [UI_OPERATION_SELECT, UI_OPERATION_SCRUB, UI_OPERATION_OPEN]
