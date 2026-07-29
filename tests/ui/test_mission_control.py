"""Mission Control adaptive modes + projection tests."""

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
    ObservationSnapshot,
    PlanSnapshot,
)
from ai_command_center.domain.execution_library_snapshot import (
    ExecutionLibrarySnapshot,
    ExecutionPlanSnapshot,
)
from ai_command_center.domain.permission_check_snapshot import (
    PendingCheck,
    PermissionCheckSnapshot,
)
from ai_command_center.domain.provider_registry_snapshot import ProviderRegistrySnapshot
from ai_command_center.domain.world_model_snapshot import WorldModelSnapshot
from ai_command_center.ui.mission_control.layout_prefs import Density, LayoutPrefs
from ai_command_center.ui.mission_control.modes import MissionMode, derive_mission_mode
from tests.ui.fake_ui import CommandCenterView


def test_derive_mode_idle_on_empty() -> None:
    assert derive_mission_mode(AppState()) == MissionMode.IDLE
    assert derive_mission_mode(None) == MissionMode.IDLE


def test_derive_mode_waiting_on_pending_approval() -> None:
    snap = AppState(
        permission_snapshot=PermissionCheckSnapshot(
            pending=PendingCheck(check_id="c1", summary="Allow?"),
        ),
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="running", total_steps=2),
        ),
    )
    assert derive_mission_mode(snap) == MissionMode.WAITING


def test_derive_mode_executing() -> None:
    snap = AppState(
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="running", total_steps=3),
        ),
    )
    assert derive_mission_mode(snap) == MissionMode.EXECUTING


def test_derive_mode_planning() -> None:
    snap = AppState(
        brain_state=BrainStateSnapshot(
            kernel_state="planning",
            last_plan=PlanSnapshot(status="planning", goal="Ship"),
        ),
    )
    assert derive_mission_mode(snap) == MissionMode.PLANNING


def test_derive_mode_failure() -> None:
    snap = AppState(
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="failed", error="boom"),
        ),
    )
    assert derive_mission_mode(snap) == MissionMode.FAILURE


def test_layout_prefs_density_and_favorites() -> None:
    prefs = LayoutPrefs()
    assert prefs.density == Density.EXPANDED
    prefs.toggle_density()
    assert prefs.is_compact()
    assert prefs.toggle_favorite("chat") is True
    assert "chat" in prefs.favorites
    prefs.record_page("goals")
    prefs.record_page("chat")
    assert prefs.recent_pages[0] == "chat"


def test_command_center_brain_and_world_projection() -> None:
    view = CommandCenterView(None, on_command=lambda _x: None, on_navigate=lambda _x: None)
    snap = AppState(
        last_event_timestamp=time.time(),
        brain_state=BrainStateSnapshot(
            recent_goals=(BrainGoalSnapshot(goal_id="g1", text="Ship feature", status="active"),),
            recent_observations=(
                ObservationSnapshot(content="note", confidence=0.9),
            ),
            kernel_state="ready",
        ),
        agent_pipeline=AgentPipelineSnapshot(
            runs=(AgentRunSnapshot(agent_id="a1", state="running", task="plan"),),
            active_run_ids=("a1",),
        ),
        provider_registry=ProviderRegistrySnapshot(total_count=2, healthy_count=2),
        execution_library=ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(status="running", total_steps=4),
            total_runs=3,
        ),
        world_model=WorldModelSnapshot(node_count=10, mutation_count=2),
    )
    view.apply_state(snap)
    assert "Ship feature" in view._brain._values["Attention"].cget("text")
    assert "%" in view._brain._values["Confidence"].cget("text")
    assert "Entities 10" in view._world._stats.cget("text")
    assert view._status_strip._pills["runtime"] is not None
