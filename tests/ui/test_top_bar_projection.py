"""Projection tests for the Phase 11A Top Bar."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.agent_pipeline_snapshot import (
    AgentPipelineSnapshot,
    AgentRunSnapshot,
)
from ai_command_center.domain.brain_state_snapshot import (
    BrainStateSnapshot,
    GoalSnapshot as BrainGoalSnapshot,
)
from ai_command_center.domain.permission_check_snapshot import PermissionCheckSnapshot
from ai_command_center.domain.settings_snapshot import SettingsSnapshot
from tests.ui.fake_ui import TopBar


def _sample_snap() -> AppState:
    return AppState(
        settings=SettingsSnapshot(default_model="llama3.2", provider="ollama"),
        brain_state=BrainStateSnapshot(
            recent_goals=(
                BrainGoalSnapshot(goal_id="g1", text="Ship feature", status="active"),
            ),
            kernel_state="ready",
        ),
        agent_pipeline=AgentPipelineSnapshot(
            active_run_ids=("a1",),
            runs=(AgentRunSnapshot(agent_id="a1", state="running"),),
        ),
        permission_snapshot=PermissionCheckSnapshot(
            total_requested=3,
            total_granted=2,
            total_denied=0,
        ),
    )


def test_top_bar_displays_active_goal_pill() -> None:
    top = TopBar(None, on_settings=lambda: None, on_close=lambda: None)
    top.update_top_bar(_sample_snap())

    assert "Ship feature" in top._active_goal_btn.cget("text")


def test_top_bar_displays_kernel_pill() -> None:
    top = TopBar(None, on_settings=lambda: None, on_close=lambda: None)
    top.update_top_bar(_sample_snap())

    assert "Ready" in top._kernel_pill._label.cget("text")


def test_top_bar_displays_agent_pill() -> None:
    top = TopBar(None, on_settings=lambda: None, on_close=lambda: None)
    top.update_top_bar(_sample_snap())

    assert "1 agent" in top._agents_pill._label.cget("text")


def test_top_bar_displays_approval_pill() -> None:
    top = TopBar(None, on_settings=lambda: None, on_close=lambda: None)
    top.update_top_bar(_sample_snap())

    assert "0 pending" in top._approvals_pill._label.cget("text")


def test_top_bar_displays_model_and_provider_pills() -> None:
    top = TopBar(None, on_settings=lambda: None, on_close=lambda: None)
    top.update_llm_status(
        provider="ollama",
        phase="ready",
        model="llama3.2",
        ollama_online=True,
        openai_online=False,
        openai_configured=False,
    )

    assert "llama3.2" in top._model_pill._label.cget("text")
    assert "Ollama" in top._provider_pill._label.cget("text")


def test_top_bar_navigation_wiring() -> None:
    navigated: list[str] = []

    def on_navigate(view_id: str) -> None:
        navigated.append(view_id)

    top = TopBar(
        None,
        on_settings=lambda: None,
        on_close=lambda: None,
        on_navigate=on_navigate,
    )
    top._on_active_goal()
    top._on_agents()
    top._on_approvals()
    top._on_model()

    assert "goals" in navigated
    assert "agents" in navigated
    assert "approvals" in navigated
    assert "providers" in navigated
