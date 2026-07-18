"""Projection tests for the Phase 11A Command Center dashboard."""

from __future__ import annotations

import time

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.agent_pipeline_snapshot import (
    AgentPipelineSnapshot,
    AgentRunSnapshot,
)
from ai_command_center.domain.brain_state_snapshot import (
    BrainStateSnapshot,
    GoalSnapshot as BrainGoalSnapshot,
)
from ai_command_center.domain.execution_library_snapshot import (
    ExecutionLibrarySnapshot,
    ExecutionPlanSnapshot,
    ExecutionRunEntry,
)
from ai_command_center.domain.permission_check_snapshot import (
    PendingCheck,
    PermissionCheckSnapshot,
)
from ai_command_center.domain.provider_registry_snapshot import ProviderRegistrySnapshot
from ai_command_center.domain.world_model_snapshot import (
    MutationSnapshot,
    WorldModelSnapshot,
)
from tests.ui.fake_ui import CommandCenterView


def _sample_snap() -> AppState:
    ts = time.time()
    return AppState(
        last_event_timestamp=ts,
        brain_state=BrainStateSnapshot(
            recent_goals=(BrainGoalSnapshot(goal_id="g1", text="Ship feature", status="active"),),
            kernel_state="ready",
        ),
        agent_pipeline=AgentPipelineSnapshot(
            runs=(AgentRunSnapshot(agent_id="a1", state="running", task="plan"),),
            active_run_ids=("a1",),
            pipeline_id="p1",
            pipeline_stage="planning",
            planned_tools=("search", "shell"),
        ),
        permission_snapshot=PermissionCheckSnapshot(
            pending=PendingCheck(
                check_id="c1",
                permissions=("read",),
                actor_id="agent_a",
                summary="Allow read?",
            ),
        ),
        provider_registry=ProviderRegistrySnapshot(total_count=2, healthy_count=2),
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="running", total_steps=3),
            total_runs=5,
            run_history=(ExecutionRunEntry(summary="run", created_at=ts),),
        ),
        world_model=WorldModelSnapshot(
            node_count=12,
            mutation_count=3,
            mutation_log=(MutationSnapshot(timestamp="2024-01-01T00:00:00", summary="added node"),),
        ),
    )


def _accepted_action_texts() -> set[str]:
    return {"Open Chat", "New Goal", "Resume Goal", "Review Approval"}


def test_hero_action_is_app_state_driven() -> None:
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
    )
    snap = _sample_snap()
    view.apply_state(snap)

    assert view._action_button.cget("text") in _accepted_action_texts()
    assert view._action_view in ("chat", "goals", "approvals")


def test_hero_displays_active_goal_and_status() -> None:
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
    )
    snap = _sample_snap()
    view.apply_state(snap)

    assert "Ship feature" in view._goal_label.cget("text")
    assert view._status_label.cget("text") == "Active"


def test_hero_summary_counts() -> None:
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
    )
    snap = _sample_snap()
    view.apply_state(snap)

    summary = view._summary_label.cget("text")
    assert "1 active goal" in summary
    assert "1 running execution" in summary
    assert "1 pending approval" in summary
    assert "1 active agent" in summary


def test_ops_cards_display_metric_status_and_timestamp() -> None:
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
    )
    snap = _sample_snap()
    view.apply_state(snap)

    for key in ("executions", "agents", "approvals", "providers"):
        card = view._ops_cards[key]
        assert card._metric.cget("text") != ""
        assert card._status.cget("text") == "●"
        assert card._sub.cget("text") != ""
        updated = card._updated.cget("text")
        assert updated.startswith("Updated")


def test_system_awareness_workspace_health() -> None:
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
    )
    snap = _sample_snap()
    view.apply_state(snap)

    for key in ("provider", "agent", "execution", "goal", "world"):
        row = view._health_rows[key]
        label = row._label.cget("text")
        assert ":" in label
        assert row._status.cget("text") == "●"


def test_system_awareness_recent_changes() -> None:
    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=lambda _x: None,
    )
    snap = _sample_snap()
    view.apply_state(snap)

    texts = [lbl.cget("text") for lbl in view._recent_changes._items]
    assert any("Mutation" in t for t in texts)


def test_hero_action_publishes_navigate_event() -> None:
    navigated: list[str] = []

    def on_navigate(view_id: str) -> None:
        navigated.append(view_id)

    view = CommandCenterView(
        None,
        on_command=lambda _x: None,
        on_navigate=on_navigate,
    )
    snap = _sample_snap()
    view.apply_state(snap)
    view._action_button.invoke()

    assert len(navigated) == 1
    assert navigated[0] == view._action_view
